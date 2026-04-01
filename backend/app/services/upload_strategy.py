"""上传策略执行逻辑。"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.integrations.p115.client import P115Gateway
from app.models.enums import DuplicateCheckMode, FileAction, UploadMode
from app.services.remote_dir_cache_service import RemoteDirCacheService
from app.services.sync_scanner import LocalFileCandidate, build_range_hash_reader, calc_sha1


@dataclass
class UploadResult:
    """单文件上传结果。"""

    action: FileAction
    message: str
    file_sha1: str | None = None
    remote_file_id: str | None = None
    remote_pickcode: str | None = None
    remote_dir_id: int | None = None
    remote_dir_path: str | None = None


class UploadStrategyService:
    """根据上传模式执行上传。"""

    def __init__(self, gateway: P115Gateway, remote_cache_service: RemoteDirCacheService, default_part_size_mb: int = 10) -> None:
        self.gateway = gateway
        self.remote_cache_service = remote_cache_service
        self.default_part_size_mb = default_part_size_mb
        self._dir_cache: dict[int, list[dict]] = {}

    def _get_remote_dir_items(
        self,
        *,
        pid: int,
        remote_dir_path: str,
        force_refresh_remote_cache: bool,
        log: Callable[[str], None] | None = None,
    ) -> list[dict]:
        if pid in self._dir_cache and not force_refresh_remote_cache:
            return self._dir_cache[pid]

        if not force_refresh_remote_cache:
            exists, cached_items = self.remote_cache_service.get_dir_entries(pid)
            if exists:
                self._dir_cache[pid] = cached_items
                if log:
                    log(f'命中本地远端目录缓存: {remote_dir_path}，共 {len(cached_items)} 个文件')
                return cached_items

        remote_items = self.gateway.list_remote_dir_files(pid=pid)
        self.remote_cache_service.replace_dir_entries(remote_dir_id=pid, remote_dir_path=remote_dir_path, items=remote_items)
        self._dir_cache[pid] = remote_items
        if log:
            action = '强制同步远端目录文件完成' if force_refresh_remote_cache else '远端目录缓存未命中，已拉取并写入本地缓存'
            log(f'{action}: {remote_dir_path}，共 {len(remote_items)} 个文件')
        return remote_items

    @staticmethod
    def _match_existing_file(items: list[dict], *, mode: DuplicateCheckMode, filename: str, filesha1: str) -> dict | None:
        if mode == DuplicateCheckMode.NAME:
            for item in items:
                if item.get('name') == filename:
                    return item
            return None
        if mode == DuplicateCheckMode.SHA1:
            target_sha1 = filesha1.upper()
            for item in items:
                if str(item.get('sha1') or '').upper() == target_sha1:
                    return item
            return None
        return None

    def _store_uploaded_file(
        self,
        *,
        remote_dir_id: int,
        remote_dir_path: str,
        filename: str,
        file_sha1: str,
        size: int,
        remote_file_id: str | None,
        remote_pickcode: str | None,
    ) -> None:
        self.remote_cache_service.upsert_file_entry(
            remote_dir_id=remote_dir_id,
            remote_dir_path=remote_dir_path,
            remote_file_id=remote_file_id,
            remote_pickcode=remote_pickcode,
            name=filename,
            sha1=file_sha1,
            size=size,
        )
        cached = self._dir_cache.setdefault(remote_dir_id, [])
        target_id = str(remote_file_id or '')
        normalized = {
            'id': target_id or f'local:{filename}:{file_sha1}',
            'pickcode': remote_pickcode,
            'name': filename,
            'sha1': file_sha1,
            'size': size,
            'is_dir': False,
        }
        if target_id:
            cached[:] = [item for item in cached if str(item.get('id') or '') != target_id]
        cached[:] = [item for item in cached if not (item.get('name') == filename and str(item.get('sha1') or '').upper() == file_sha1.upper())]
        cached.append(normalized)

    def upload_candidate(
        self,
        candidate: LocalFileCandidate,
        remote_root: str,
        upload_mode: UploadMode,
        *,
        duplicate_check_mode: DuplicateCheckMode = DuplicateCheckMode.NONE,
        force_refresh_remote_cache: bool = False,
        log: Callable[[str], None] | None = None,
    ) -> UploadResult:
        remote_root_path = PurePosixPath(remote_root)
        remote_dir = remote_root_path.joinpath(*candidate.relative_path.parts[:-1]) if candidate.relative_path.parts[:-1] else remote_root_path
        remote_dir_path = remote_dir.as_posix()
        pid = self.gateway.ensure_remote_dir(remote_dir)
        file_sha1 = calc_sha1(candidate.absolute_path)
        range_reader = build_range_hash_reader(candidate.absolute_path)

        if duplicate_check_mode != DuplicateCheckMode.NONE:
            existing = self._match_existing_file(
                self._get_remote_dir_items(
                    pid=pid,
                    remote_dir_path=remote_dir_path,
                    force_refresh_remote_cache=force_refresh_remote_cache,
                    log=log,
                ),
                mode=duplicate_check_mode,
                filename=candidate.absolute_path.name,
                filesha1=file_sha1,
            )
            if existing is not None:
                mode_text = '按文件名' if duplicate_check_mode == DuplicateCheckMode.NAME else '按 SHA1'
                return UploadResult(
                    action=FileAction.SKIPPED,
                    message=f"远端目录已存在文件，{mode_text}匹配命中，按配置跳过 (id={existing.get('id')}, pickcode={existing.get('pickcode')})",
                    file_sha1=file_sha1,
                    remote_file_id=str(existing.get('id') or '') or None,
                    remote_pickcode=existing.get('pickcode'),
                    remote_dir_id=pid,
                    remote_dir_path=remote_dir_path,
                )

        if upload_mode != UploadMode.MULTIPART_ONLY:
            init_resp = self.gateway.fast_upload_init(
                filename=candidate.absolute_path.name,
                filesize=candidate.size,
                filesha1=file_sha1,
                pid=pid,
                read_range_hash=range_reader,
            )
            if init_resp.get('reuse'):
                data = init_resp.get('data', {})
                remote_file_id = str(data.get('file_id') or '') or None
                remote_pickcode = data.get('pickcode')
                self._store_uploaded_file(
                    remote_dir_id=pid,
                    remote_dir_path=remote_dir_path,
                    filename=candidate.absolute_path.name,
                    file_sha1=file_sha1,
                    size=candidate.size,
                    remote_file_id=remote_file_id,
                    remote_pickcode=remote_pickcode,
                )
                return UploadResult(
                    action=FileAction.FAST_UPLOADED,
                    message='秒传成功',
                    file_sha1=file_sha1,
                    remote_file_id=remote_file_id,
                    remote_pickcode=remote_pickcode,
                    remote_dir_id=pid,
                    remote_dir_path=remote_dir_path,
                )
            if upload_mode == UploadMode.FAST_ONLY:
                return UploadResult(action=FileAction.SKIPPED, message='未命中秒传，按配置跳过', file_sha1=file_sha1, remote_dir_id=pid, remote_dir_path=remote_dir_path)

        response = self.gateway.multipart_upload(
            file_path=candidate.absolute_path,
            pid=pid,
            filename=candidate.absolute_path.name,
            partsize=self.default_part_size_mb * 1024 * 1024,
        )
        data = response.get('data', response)
        remote_file_id = str(data.get('file_id') or '') or None
        remote_pickcode = data.get('pickcode')
        self._store_uploaded_file(
            remote_dir_id=pid,
            remote_dir_path=remote_dir_path,
            filename=candidate.absolute_path.name,
            file_sha1=file_sha1,
            size=candidate.size,
            remote_file_id=remote_file_id,
            remote_pickcode=remote_pickcode,
        )
        return UploadResult(
            action=FileAction.MULTIPART_UPLOADED,
            message='分片上传完成',
            file_sha1=file_sha1,
            remote_file_id=remote_file_id,
            remote_pickcode=remote_pickcode,
            remote_dir_id=pid,
            remote_dir_path=remote_dir_path,
        )
