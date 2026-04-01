"""上传策略执行逻辑。"""

from dataclasses import dataclass
from pathlib import PurePosixPath

from app.integrations.p115.client import P115Gateway
from app.models.enums import FileAction, UploadMode
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

    def upload_candidate(
        self,
        candidate: LocalFileCandidate,
        remote_root: str,
        upload_mode: UploadMode,
        *,
        skip_existing_remote: bool = False,
    ) -> UploadResult:
        remote_root_path = PurePosixPath(remote_root)
        remote_dir = remote_root_path.joinpath(*candidate.relative_path.parts[:-1]) if candidate.relative_path.parts[:-1] else remote_root_path
        pid = self.gateway.ensure_remote_dir(remote_dir)
        file_sha1 = calc_sha1(candidate.absolute_path)
        range_reader = build_range_hash_reader(candidate.absolute_path)

        if skip_existing_remote:
            existing = self.gateway.find_existing_remote_file(
                pid=pid,
                filename=candidate.absolute_path.name,
                filesize=candidate.size,
                filesha1=file_sha1,
            )
            if existing is not None:
                return UploadResult(
                    action=FileAction.SKIPPED,
                    message=f"远端已存在同名文件，按防重复上传配置跳过 (id={existing.get('id')}, pickcode={existing.get('pickcode')})",
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
