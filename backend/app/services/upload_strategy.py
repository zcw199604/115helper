"""上传策略执行逻辑。"""

from dataclasses import dataclass
from pathlib import PurePosixPath

from app.integrations.p115.client import P115Gateway
from app.models.enums import DuplicateCheckMode, FileAction, UploadMode
from app.services.sync_scanner import LocalFileCandidate, build_range_hash_reader, calc_sha1


@dataclass
class UploadResult:
    """单文件上传结果。"""

    action: FileAction
    message: str
    file_sha1: str | None = None
    remote_file_id: str | None = None
    remote_pickcode: str | None = None


class UploadStrategyService:
    """根据上传模式执行上传。"""

    def __init__(self, gateway: P115Gateway, default_part_size_mb: int = 10) -> None:
        self.gateway = gateway
        self.default_part_size_mb = default_part_size_mb
        self._dir_cache: dict[int, list[dict]] = {}

    def _get_remote_dir_items(self, pid: int) -> list[dict]:
        if pid not in self._dir_cache:
            self._dir_cache[pid] = self.gateway.list_remote_dir_files(pid=pid)
        return self._dir_cache[pid]

    @staticmethod
    def _match_existing_file(items: list[dict], *, mode: DuplicateCheckMode, filename: str, filesha1: str) -> dict | None:
        if mode == DuplicateCheckMode.NAME:
            for item in items:
                if item.get("name") == filename:
                    return item
            return None
        if mode == DuplicateCheckMode.SHA1:
            target_sha1 = filesha1.upper()
            for item in items:
                if str(item.get("sha1") or "").upper() == target_sha1:
                    return item
            return None
        return None

    def upload_candidate(
        self,
        candidate: LocalFileCandidate,
        remote_root: str,
        upload_mode: UploadMode,
        *,
        duplicate_check_mode: DuplicateCheckMode = DuplicateCheckMode.NONE,
    ) -> UploadResult:
        remote_root_path = PurePosixPath(remote_root)
        remote_dir = remote_root_path.joinpath(*candidate.relative_path.parts[:-1]) if candidate.relative_path.parts[:-1] else remote_root_path
        pid = self.gateway.ensure_remote_dir(remote_dir)
        file_sha1 = calc_sha1(candidate.absolute_path)
        range_reader = build_range_hash_reader(candidate.absolute_path)

        if duplicate_check_mode != DuplicateCheckMode.NONE:
            existing = self._match_existing_file(
                self._get_remote_dir_items(pid),
                mode=duplicate_check_mode,
                filename=candidate.absolute_path.name,
                filesha1=file_sha1,
            )
            if existing is not None:
                mode_text = "按文件名" if duplicate_check_mode == DuplicateCheckMode.NAME else "按 SHA1"
                return UploadResult(
                    action=FileAction.SKIPPED,
                    message=f"远端目录已存在文件，{mode_text}匹配命中，按配置跳过 (id={existing.get('id')}, pickcode={existing.get('pickcode')})",
                    file_sha1=file_sha1,
                    remote_file_id=str(existing.get('id') or '') or None,
                    remote_pickcode=existing.get('pickcode'),
                )

        if upload_mode != UploadMode.MULTIPART_ONLY:
            init_resp = self.gateway.fast_upload_init(
                filename=candidate.absolute_path.name,
                filesize=candidate.size,
                filesha1=file_sha1,
                pid=pid,
                read_range_hash=range_reader,
            )
            if init_resp.get("reuse"):
                data = init_resp.get("data", {})
                return UploadResult(
                    action=FileAction.FAST_UPLOADED,
                    message="秒传成功",
                    file_sha1=file_sha1,
                    remote_file_id=str(data.get("file_id") or "") or None,
                    remote_pickcode=data.get("pickcode"),
                )
            if upload_mode == UploadMode.FAST_ONLY:
                return UploadResult(action=FileAction.SKIPPED, message="未命中秒传，按配置跳过", file_sha1=file_sha1)

        response = self.gateway.multipart_upload(
            file_path=candidate.absolute_path,
            pid=pid,
            filename=candidate.absolute_path.name,
            partsize=self.default_part_size_mb * 1024 * 1024,
        )
        data = response.get("data", response)
        return UploadResult(
            action=FileAction.MULTIPART_UPLOADED,
            message="分片上传完成",
            file_sha1=file_sha1,
            remote_file_id=str(data.get("file_id") or "") or None,
            remote_pickcode=data.get("pickcode"),
        )
