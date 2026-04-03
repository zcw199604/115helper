"""115 客户端封装，隔离第三方依赖细节。"""

from pathlib import Path, PurePosixPath
from typing import Callable

from app.core.config import get_settings
from app.integrations.p115.open_uploader import P115OpenUploader

IOS_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 115wangpan_ios/36.2.20"
)


class P115Gateway:
    """负责目录解析与上传调用。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        self._open_uploader = P115OpenUploader(self.settings)

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
        for token in ["UID=", "CID=", "SEID=", "KID=", "authorization", "refresh_token", "access_token", "Bearer "]:
            if token.lower() in text.lower():
                return "115 接口调用失败，错误信息已脱敏"
        return text or exc.__class__.__name__

    def get_dir_id_by_path(self, remote_dir: PurePosixPath) -> int:
        path_str = remote_dir.as_posix()
        if path_str == "/":
            return 0
        for lookup in (
            lambda: self.client.fs_dir_getid(path_str, **self.request_kwargs(app=False)),
            lambda: self.client.fs_dir_getid_app(path_str, **self.request_kwargs()),
        ):
            try:
                response = lookup()
                directory_id = int(response.get("id", 0))
                if directory_id > 0:
                    return directory_id
            except Exception:
                continue
        return 0

    def ensure_remote_dir(self, remote_dir: PurePosixPath) -> int:
        path_str = remote_dir.as_posix()
        if path_str == "/":
            return 0
        directory_id = self.get_dir_id_by_path(remote_dir)
        if directory_id > 0:
            return directory_id
        response = self.client.fs_makedirs_app(path_str, pid=0, **self.request_kwargs())
        return int(response["cid"])

    @staticmethod
    def _normalize_remote_item(item: dict) -> dict:
        raw_id = item.get("fid") or item.get("cid") or item.get("file_id") or item.get("id")
        is_dir = bool(
            item.get("is_dir")
            or item.get("fc")
            or item.get("category") == "dir"
            or (item.get("cid") not in (None, "") and item.get("fid") in (None, ""))
        )
        return {
            "id": raw_id,
            "pickcode": item.get("pc") or item.get("pick_code") or item.get("pickcode"),
            "name": item.get("n") or item.get("fn") or item.get("file_name") or item.get("name"),
            "size": item.get("s") or item.get("fs") or item.get("file_size") or item.get("size"),
            "sha1": item.get("sha") or item.get("sha1") or item.get("file_sha1") or "",
            "is_dir": is_dir,
        }

    def list_remote_dir_entries(self, *, pid: int, include_dirs: bool = True) -> list[dict]:
        offset = 0
        limit = 200
        result: list[dict] = []
        show_dir = 1 if include_dirs else 0
        while True:
            response = self.client.fs_files(
                {"cid": pid, "limit": limit, "offset": offset, "show_dir": show_dir},
                **self.request_kwargs(app=False),
            )
            items = response.get("data") or []
            if not isinstance(items, list):
                break
            normalized_items = [self._normalize_remote_item(item) for item in items]
            if not include_dirs:
                normalized_items = [item for item in normalized_items if not item.get("is_dir")]
            result.extend(normalized_items)
            if len(items) < limit:
                break
            offset += limit
        return result

    def list_remote_dir_files(self, *, pid: int) -> list[dict]:
        return self.list_remote_dir_entries(pid=pid, include_dirs=False)

    def find_child_dir(self, *, parent_id: int, name: str) -> dict | None:
        for item in self.list_remote_dir_entries(pid=parent_id, include_dirs=True):
            if item.get("is_dir") and item.get("name") == name:
                return item
        return None

    def create_child_dir(self, *, parent_id: int, name: str) -> dict:
        response = self.client.fs_mkdir({"cname": name, "pid": parent_id}, **self.request_kwargs(app=False))
        raw_id = response.get("cid") or response.get("file_id") or response.get("id")
        if not raw_id:
            raise RuntimeError(f"115 创建目录失败: {response}")
        return {
            "id": int(raw_id),
            "pickcode": self.client.to_pickcode(int(raw_id)) if hasattr(self.client, "to_pickcode") else None,
            "name": name,
            "size": None,
            "sha1": "",
            "is_dir": True,
        }

    def ensure_remote_dir_plugin_style(self, remote_dir: PurePosixPath) -> int:
        normalized = PurePosixPath(remote_dir).as_posix()
        if normalized == "/":
            return 0
        existing_id = self.get_dir_id_by_path(PurePosixPath(normalized))
        if existing_id > 0:
            return existing_id

        current_path = PurePosixPath("/")
        current_id = 0
        for part in PurePosixPath(normalized).parts[1:]:
            current_path = current_path.joinpath(part)
            existing_id = self.get_dir_id_by_path(current_path)
            if existing_id > 0:
                current_id = existing_id
                continue
            child_dir = self.find_child_dir(parent_id=current_id, name=part)
            if child_dir is not None:
                current_id = int(child_dir["id"])
                continue
            created = self.create_child_dir(parent_id=current_id, name=part)
            current_id = int(created["id"])
        return current_id

    def get_remote_file_by_path(self, remote_file_path: PurePosixPath) -> dict | None:
        normalized = PurePosixPath(remote_file_path)
        parent_path = normalized.parent
        parent_id = self.get_dir_id_by_path(parent_path)
        if parent_id < 0 or (parent_id == 0 and parent_path.as_posix() != "/"):
            return None
        for item in self.list_remote_dir_entries(pid=parent_id, include_dirs=True):
            if item.get("is_dir"):
                continue
            if item.get("name") == normalized.name:
                return item
        return None

    def fast_upload_init(self, *, filename: str, filesize: int, filesha1: str, pid: int, read_range_hash: Callable[[str], str]) -> dict:
        return self.client.upload_file_init(
            filename=filename,
            filesize=filesize,
            filesha1=filesha1,
            pid=pid,
            read_range_bytes_or_hash=read_range_hash,
        )

    def multipart_upload(
        self,
        *,
        file_path: Path,
        pid: int,
        filename: str,
        partsize: int,
        log: Callable[[str], None] | None = None,
        is_cancel_requested: Callable[[], bool] | None = None,
    ) -> dict:
        if self._open_uploader.enabled:
            return self._open_uploader.upload(
                file_path=file_path,
                pid=pid,
                filename=filename,
                partsize=partsize,
                log=log,
                is_cancel_requested=is_cancel_requested,
            )
        if log is not None:
            log("未配置 115 Open 凭证，回退至 p115client 分片上传")
        return self.client.upload_file(
            file=file_path,
            pid=pid,
            filename=filename,
            partsize=partsize,
        )
