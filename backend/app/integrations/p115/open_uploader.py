"""基于 115 Open API 的上传实现，尽量对齐 plugin 的上传链路。"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from threading import Lock
from typing import Callable

import httpx
from oss2 import Bucket, SizedFileAdapter, StsAuth, determine_part_size
from oss2.exceptions import OssError
from oss2.models import PartInfo
from oss2.utils import b64encode_as_string

from app.core.config import Settings


class OpenUploadCancelled(RuntimeError):
    """Open 上传过程中收到取消请求。"""


class P115OpenUploader:
    """115 Open API 上传器。"""

    base_url = "https://proapi.115.com"
    refresh_url = "https://passportapi.115.com/open/refreshToken"
    preid_size = 128 * 1024 * 1024

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=20.0,
            headers={
                "User-Agent": "W115Storage/2.0",
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        self._lock = Lock()
        self._access_token = settings.p115_open_access_token.strip()
        self._expires_at = 0
        if self._access_token:
            self._client.headers.update({"Authorization": f"Bearer {self._access_token}"})

    @property
    def enabled(self) -> bool:
        return bool(self.settings.p115_open_refresh_token or self._access_token)

    def _ensure_access_token(self, *, force_refresh: bool = False) -> str:
        with self._lock:
            if self._access_token and not force_refresh:
                if self._expires_at <= 0 or time.time() < self._expires_at - 60:
                    return self._access_token
            refresh_token = self.settings.p115_open_refresh_token.strip()
            if not refresh_token:
                raise RuntimeError("未配置 115 Open Refresh Token，无法使用 Open 上传")
            response = self._client.post(self.refresh_url, data={"refresh_token": refresh_token})
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                message = payload.get("message") or "刷新 access_token 失败"
                raise RuntimeError(f"115 Open 鉴权失败: {message}")
            data = payload.get("data") or {}
            access_token = str(data.get("access_token") or "").strip()
            if not access_token:
                raise RuntimeError("115 Open 未返回 access_token")
            self._access_token = access_token
            expires_in = int(data.get("expires_in") or 0)
            self._expires_at = int(time.time()) + expires_in if expires_in > 0 else 0
            self._client.headers.update({"Authorization": f"Bearer {access_token}"})
            return access_token

    def _request_api(self, method: str, endpoint: str, *, retry_limit: int = 3, allow_refresh: bool = True, **kwargs) -> dict:
        self._ensure_access_token()
        response = self._client.request(method, f"{self.base_url}{endpoint}", **kwargs)
        if response.status_code in {401, 403} and allow_refresh:
            self._ensure_access_token(force_refresh=True)
            return self._request_api(method, endpoint, retry_limit=retry_limit, allow_refresh=False, **kwargs)
        if response.status_code == 429 and retry_limit > 0:
            sleep_time = 5 + int(response.headers.get("X-RateLimit-Reset", 5))
            time.sleep(sleep_time)
            return self._request_api(method, endpoint, retry_limit=retry_limit - 1, allow_refresh=allow_refresh, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            message = payload.get("message") or payload.get("error") or "115 Open 接口调用失败"
            raise RuntimeError(message)
        return payload

    @staticmethod
    def _calc_sha1(file_path: Path, size: int | None = None) -> str:
        digest = hashlib.sha1()
        with file_path.open("rb") as handle:
            if size is None:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            else:
                remaining = size
                while remaining > 0:
                    chunk = handle.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    digest.update(chunk)
                    remaining -= len(chunk)
        return digest.hexdigest().upper()

    @staticmethod
    def _calc_range_sha1(file_path: Path, sign_check: str) -> str:
        start_str, end_str = sign_check.split("-")
        start = int(start_str)
        end = int(end_str)
        digest = hashlib.sha1()
        with file_path.open("rb") as handle:
            handle.seek(start)
            digest.update(handle.read(end - start + 1))
        return digest.hexdigest().upper()

    @staticmethod
    def _unwrap_data(payload: dict) -> dict:
        data = payload.get("data")
        if isinstance(data, dict) and data:
            return data
        return payload

    @staticmethod
    def _encode_callback(payload: str) -> str:
        return b64encode_as_string(payload.encode("utf-8"))

    def upload(
        self,
        *,
        file_path: Path,
        pid: int,
        filename: str,
        partsize: int,
        log: Callable[[str], None] | None = None,
        is_cancel_requested: Callable[[], bool] | None = None,
    ) -> dict:
        file_size = file_path.stat().st_size
        file_sha1 = self._calc_sha1(file_path)
        file_preid = self._calc_sha1(file_path, min(file_size, self.preid_size))
        target = f"U_1_{pid}"

        def emit(message: str) -> None:
            if log is not None:
                log(message)

        def check_cancel(stage: str) -> None:
            if is_cancel_requested and is_cancel_requested():
                raise OpenUploadCancelled(f"上传已取消: {stage}")

        emit(f"Open 上传初始化: {filename}，大小 {file_size} bytes")
        check_cancel("init")
        init_data = {
            "file_name": filename,
            "file_size": file_size,
            "target": target,
            "fileid": file_sha1,
            "preid": file_preid,
        }
        init_result = self._unwrap_data(self._request_api("POST", "/open/upload/init", data=init_data, timeout=120.0))

        if init_result.get("code") in {700, 701} and init_result.get("sign_check"):
            sign_val = self._calc_range_sha1(file_path, str(init_result["sign_check"]))
            emit(f"Open 上传触发二次校验: {filename}，区间 {init_result['sign_check']}")
            init_data.update(
                {
                    "pick_code": init_result.get("pick_code"),
                    "sign_key": init_result.get("sign_key"),
                    "sign_val": sign_val,
                }
            )
            check_cancel("second-auth")
            init_result = self._unwrap_data(self._request_api("POST", "/open/upload/init", data=init_data, timeout=120.0))

        if init_result.get("status") == 2:
            emit(f"Open 上传命中秒传: {filename}")
            return {
                "reuse": True,
                "data": {
                    "file_id": init_result.get("file_id"),
                    "pickcode": init_result.get("pick_code") or init_result.get("pickcode"),
                },
                "filesha1": file_sha1,
            }

        bucket_name = init_result.get("bucket")
        object_name = init_result.get("object")
        callback = init_result.get("callback") or {}
        pick_code = init_result.get("pick_code")
        if not bucket_name or not object_name:
            raise RuntimeError("115 Open 初始化未返回对象存储信息")

        emit(f"Open 上传获取凭证: {filename}")
        token_payload = self._unwrap_data(self._request_api("GET", "/open/upload/get_token", timeout=120.0))
        endpoint = token_payload.get("endpoint")
        access_key_id = token_payload.get("AccessKeyId")
        access_key_secret = token_payload.get("AccessKeySecret")
        security_token = token_payload.get("SecurityToken")
        if not all([endpoint, access_key_id, access_key_secret, security_token]):
            raise RuntimeError("115 Open 上传凭证不完整")

        resume_payload = self._unwrap_data(
            self._request_api(
                "POST",
                "/open/upload/resume",
                data={
                    "file_size": file_size,
                    "target": target,
                    "fileid": file_sha1,
                    "pick_code": pick_code,
                },
                timeout=120.0,
            )
        )
        if resume_payload.get("callback"):
            callback = resume_payload["callback"]

        auth = StsAuth(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=security_token,
        )
        bucket = Bucket(auth, endpoint, bucket_name, connect_timeout=120)
        actual_part_size = determine_part_size(file_size, preferred_size=partsize)

        emit(f"Open 分片上传开始: {filename}，分片大小 {actual_part_size} bytes")
        upload_id = None
        for attempt in range(3):
            check_cancel("init-multipart")
            try:
                upload_id = bucket.init_multipart_upload(
                    object_name,
                    params={"encoding-type": "url", "sequential": ""},
                ).upload_id
                break
            except Exception as exc:
                if attempt == 2:
                    raise RuntimeError(f"初始化 Open 分片上传失败: {exc}") from exc
                emit(f"Open 初始化分片失败，准备重试 {attempt + 2}/3: {exc}")
                time.sleep(2**attempt)
        if not upload_id:
            raise RuntimeError("初始化 Open 分片上传失败")

        parts: list[PartInfo] = []
        with file_path.open("rb") as handle:
            part_number = 1
            offset = 0
            while offset < file_size:
                check_cancel(f"part-{part_number}")
                current_size = min(actual_part_size, file_size - offset)
                for attempt in range(3):
                    try:
                        handle.seek(offset)
                        emit(f"Open 上传分片 {part_number}: {offset} -> {offset + current_size}")
                        result = bucket.upload_part(
                            object_name,
                            upload_id,
                            part_number,
                            data=SizedFileAdapter(handle, current_size),
                        )
                        parts.append(PartInfo(part_number, result.etag))
                        break
                    except OssError as exc:
                        if exc.code == "SecurityTokenExpired":
                            emit(f"Open 上传凭证过期，刷新后重试分片 {part_number}")
                            token_payload = self._unwrap_data(self._request_api("GET", "/open/upload/get_token", timeout=120.0))
                            auth = StsAuth(
                                access_key_id=token_payload.get("AccessKeyId"),
                                access_key_secret=token_payload.get("AccessKeySecret"),
                                security_token=token_payload.get("SecurityToken"),
                            )
                            bucket = Bucket(auth, token_payload.get("endpoint"), bucket_name, connect_timeout=120)
                            continue
                        if attempt == 2:
                            raise RuntimeError(f"Open 上传分片失败: {exc.code} {exc.message}") from exc
                        emit(f"Open 上传分片 {part_number} 失败，准备重试 {attempt + 2}/3: {exc}")
                        time.sleep(2**attempt)
                    except Exception as exc:
                        if attempt == 2:
                            raise RuntimeError(f"Open 上传分片失败: {exc}") from exc
                        emit(f"Open 上传分片 {part_number} 异常，准备重试 {attempt + 2}/3: {exc}")
                        time.sleep(2**attempt)
                offset += current_size
                part_number += 1

        headers = {"x-oss-forbid-overwrite": "false"}
        if callback.get("callback"):
            headers["X-oss-callback"] = self._encode_callback(callback["callback"])
        if callback.get("callback_var"):
            headers["x-oss-callback-var"] = self._encode_callback(callback["callback_var"])

        emit(f"Open 分片上传完成，提交合并: {filename}")
        try:
            result = bucket.complete_multipart_upload(object_name, upload_id, parts, headers=headers)
        except OssError as exc:
            if exc.code == "InvalidAccessKeyId":
                raise RuntimeError("Open 上传凭证失效，请重试任务") from exc
            raise RuntimeError(f"Open 合并分片失败: {exc.code} {exc.message}") from exc
        if result.status != 200:
            raise RuntimeError(f"Open 合并分片失败，状态码: {result.status}")

        response_data: dict = {}
        try:
            response_data = result.resp.response.json()
        except Exception:
            response_data = {}
        if response_data.get("state") is False:
            raise RuntimeError(response_data.get("error") or "Open 回调返回上传失败")
        callback_data = self._unwrap_data(response_data) if response_data else {}
        emit(f"Open 上传成功: {filename}")
        return {
            "reuse": False,
            "data": {
                "file_id": callback_data.get("file_id") or callback_data.get("id"),
                "pickcode": callback_data.get("pick_code") or callback_data.get("pickcode") or pick_code,
            },
            "filesha1": file_sha1,
        }
