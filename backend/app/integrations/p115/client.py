"""115 客户端封装，隔离第三方依赖细节。"""

from pathlib import Path, PurePosixPath
from typing import Callable

from app.core.config import get_settings

IOS_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 115wangpan_ios/36.2.20"
)


class P115Gateway:
    """负责目录解析与上传调用。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    def _create_client(self):
        from p115client import P115Client

        cookies = self.settings.p115_cookies
        if not cookies and self.settings.p115_cookies_file:
            cookies = Path(self.settings.p115_cookies_file).read_text(encoding="utf-8").strip()
        if not cookies:
            raise RuntimeError("未配置 115 Cookie")
        return P115Client(cookies=cookies, check_for_relogin=self.settings.p115_check_for_relogin)

    @property
    def client(self):
        if self._client is None:
            self._client = self._create_client()
        return self._client

    @staticmethod
    def request_kwargs(app: bool = True) -> dict:
        kwargs = {"headers": {"user-agent": IOS_UA}}
        if app:
            kwargs["app"] = "ios"
        return kwargs

    @staticmethod
    def humanize_error(exc: Exception) -> str:
        text = str(exc)
        for token in ["UID=", "CID=", "SEID=", "KID=", "authorization"]:
            if token.lower() in text.lower():
                return "115 接口调用失败，错误信息已脱敏"
        return text or exc.__class__.__name__

    def ensure_remote_dir(self, remote_dir: PurePosixPath) -> int:
        path_str = remote_dir.as_posix()
        if path_str == "/":
            return 0
        try:
            response = self.client.fs_dir_getid(path_str, **self.request_kwargs(app=False))
            directory_id = int(response.get("id", 0))
            if directory_id > 0:
                return directory_id
        except Exception:
            pass
        response = self.client.fs_makedirs_app(path_str, pid=0, **self.request_kwargs())
        return int(response["cid"])

    @staticmethod
    def _normalize_remote_item(item: dict) -> dict:
        return {
            "id": item.get("fid") or item.get("file_id") or item.get("id"),
            "pickcode": item.get("pc") or item.get("pick_code") or item.get("pickcode"),
            "name": item.get("n") or item.get("fn") or item.get("file_name") or item.get("name"),
            "size": item.get("s") or item.get("fs") or item.get("file_size") or item.get("size"),
            "sha1": item.get("sha") or item.get("sha1") or item.get("file_sha1") or "",
        }

    def find_existing_remote_file(self, *, pid: int, filename: str, filesize: int, filesha1: str) -> dict | None:
        offset = 0
        limit = 200
        target_sha1 = filesha1.upper()
        while True:
            response = self.client.fs_files(
                {"cid": pid, "limit": limit, "offset": offset, "show_dir": 0, "search_value": filename},
                **self.request_kwargs(app=False),
            )
            items = response.get("data") or []
            if not isinstance(items, list):
                break
            for item in items:
                normalized = self._normalize_remote_item(item)
                if normalized["name"] != filename:
                    continue
                remote_sha1 = str(normalized["sha1"] or "").upper()
                try:
                    remote_size = int(normalized["size"] or 0)
                except (TypeError, ValueError):
                    remote_size = 0
                if remote_sha1:
                    if remote_sha1 == target_sha1:
                        return normalized
                    continue
                if remote_size == filesize:
                    return normalized
            if len(items) < limit:
                break
            offset += limit
        return None

    def fast_upload_init(self, *, filename: str, filesize: int, filesha1: str, pid: int, read_range_hash: Callable[[str], str]) -> dict:
        return self.client.upload_file_init(
            filename=filename,
            filesize=filesize,
            filesha1=filesha1,
            pid=pid,
            read_range_bytes_or_hash=read_range_hash,
        )

    def multipart_upload(self, *, file_path: Path, pid: int, filename: str, partsize: int) -> dict:
        return self.client.upload_file(
            file=file_path,
            pid=pid,
            filename=filename,
            partsize=partsize,
        )
