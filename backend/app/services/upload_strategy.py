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


@dataclass
class RemoteDirInfo:
    """对齐 plugin `_get_folder` 语义的远端目录对象。"""

    remote_dir_id: int
    remote_dir_path: str


@dataclass
class RemoteDirContext:
    """远端目录批处理上下文。"""

    remote_dir_id: int
    remote_dir_path: str
    items: list[dict]


class UploadStrategyService:
    """根据上传模式执行上传。"""

    def __init__(self, gateway: P115Gateway, remote_cache_service: RemoteDirCacheService, default_part_size_mb: int = 10) -> None:
        self.gateway = gateway
        self.remote_cache_service = remote_cache_service
        self.default_part_size_mb = default_part_size_mb
        self._dir_cache: dict[int, list[dict]] = {}
        self._dir_id_cache: dict[str, int] = {}
        self._folder_cache: dict[str, RemoteDirInfo] = {}

    def _get_folder(self, remote_dir_path: str) -> RemoteDirInfo:
        """获取远端目录；如果不存在则创建，并缓存目录对象。"""

        normalized_path = PurePosixPath(remote_dir_path).as_posix()
        cached = self._folder_cache.get(normalized_path)
        if cached is not None:
            return cached
        remote_dir_id = self._dir_id_cache.get(normalized_path)
        if remote_dir_id is None:
            remote_dir_id = self.gateway.ensure_remote_dir(PurePosixPath(normalized_path))
            self._dir_id_cache[normalized_path] = remote_dir_id
        folder = RemoteDirInfo(remote_dir_id=remote_dir_id, remote_dir_path=normalized_path)
        self._folder_cache[normalized_path] = folder
        return folder

    def resolve_remote_dir(self, remote_dir_path: str) -> int:
        return self._get_folder(remote_dir_path).remote_dir_id

    @staticmethod
    def collect_leaf_remote_dirs(remote_dir_paths: list[str]) -> list[str]:
        """收集远端目录中的叶子目录，利用递归建目录避免重复创建父级。"""

        normalized = sorted({PurePosixPath(path).as_posix() for path in remote_dir_paths})
        leaf_dirs: list[str] = []
        pure_paths = [PurePosixPath(path) for path in normalized]
        for candidate in pure_paths:
            is_parent = any(candidate != other and candidate in other.parents for other in pure_paths)
            if not is_parent:
                leaf_dirs.append(candidate.as_posix())
        return leaf_dirs

    def precreate_remote_dirs(
        self,
        remote_dir_paths: list[str],
        *,
        log: Callable[[str], None] | None = None,
        is_cancel_requested: Callable[[], bool] | None = None,
    ) -> dict[str, int]:
        """按 plugin 的方式先收集叶子目录并预创建。"""

        leaf_dirs = self.collect_leaf_remote_dirs(remote_dir_paths)
        created: dict[str, int] = {}
        if log:
            log(f"开始预创建远端叶子目录，共 {len(leaf_dirs)} 个")
        for remote_dir_path in leaf_dirs:
            if is_cancel_requested and is_cancel_requested():
                raise RuntimeError('预创建远端目录时检测到取消请求')
            folder = self._get_folder(remote_dir_path)
            created[remote_dir_path] = folder.remote_dir_id
            if log:
                log(f"远端叶子目录已就绪: {folder.remote_dir_path} (id={folder.remote_dir_id})")
        return created

    def prepare_dir_context(
        self,
        *,
        remote_dir_path: str,
        force_refresh_remote_cache: bool,
        log: Callable[[str], None] | None = None,
    ) -> RemoteDirContext:
        folder = self._get_folder(remote_dir_path)
        items = self._get_remote_dir_items(
            pid=folder.remote_dir_id,
            remote_dir_path=folder.remote_dir_path,
            force_refresh_remote_cache=force_refresh_remote_cache,
            log=log,
        )
        return RemoteDirContext(remote_dir_id=folder.remote_dir_id, remote_dir_path=folder.remote_dir_path, items=items)

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
    def _match_existing_file(items: list[dict], *, mode: DuplicateCheckMode, filename: str, filesha1: str | None = None) -> dict | None:
        if mode == DuplicateCheckMode.NAME:
            for item in items:
                if item.get('name') == filename:
                    return item
            return None
        if mode == DuplicateCheckMode.SHA1 and filesha1:
            target_sha1 = filesha1.upper()
            for item in items:
                if str(item.get('sha1') or '').upper() == target_sha1:
                    return item
            return None
        return None

    @staticmethod
    def _ensure_sha1(candidate: LocalFileCandidate, current_sha1: str | None) -> str:
        return current_sha1 or calc_sha1(candidate.absolute_path)

    def _store_uploaded_file(
        self,
        *,
        context: RemoteDirContext,
        filename: str,
        file_sha1: str,
        size: int,
        remote_file_id: str | None,
        remote_pickcode: str | None,
    ) -> None:
        self.remote_cache_service.upsert_file_entry(
            remote_dir_id=context.remote_dir_id,
            remote_dir_path=context.remote_dir_path,
            remote_file_id=remote_file_id,
            remote_pickcode=remote_pickcode,
            name=filename,
            sha1=file_sha1,
            size=size,
        )
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
            context.items[:] = [item for item in context.items if str(item.get('id') or '') != target_id]
        context.items[:] = [
            item
            for item in context.items
            if not (item.get('name') == filename and str(item.get('sha1') or '').upper() == file_sha1.upper())
        ]
        context.items.append(normalized)
        self._dir_cache[context.remote_dir_id] = context.items

    def upload_candidate_in_context(
        self,
        candidate: LocalFileCandidate,
        context: RemoteDirContext,
        upload_mode: UploadMode,
        *,
        duplicate_check_mode: DuplicateCheckMode = DuplicateCheckMode.NONE,
        log: Callable[[str], None] | None = None,
        is_cancel_requested: Callable[[], bool] | None = None,
    ) -> UploadResult:
        file_sha1: str | None = None

        if duplicate_check_mode == DuplicateCheckMode.NAME:
            existing = self._match_existing_file(context.items, mode=duplicate_check_mode, filename=candidate.absolute_path.name)
            if existing is not None:
                return UploadResult(
                    action=FileAction.SKIPPED,
                    message=f"远端目录已存在文件，按文件名匹配命中，按配置跳过 (id={existing.get('id')}, pickcode={existing.get('pickcode')})",
                    remote_file_id=str(existing.get('id') or '') or None,
                    remote_pickcode=existing.get('pickcode'),
                    remote_dir_id=context.remote_dir_id,
                    remote_dir_path=context.remote_dir_path,
                )
        elif duplicate_check_mode == DuplicateCheckMode.SHA1:
            file_sha1 = self._ensure_sha1(candidate, file_sha1)
            existing = self._match_existing_file(context.items, mode=duplicate_check_mode, filename=candidate.absolute_path.name, filesha1=file_sha1)
            if existing is not None:
                return UploadResult(
                    action=FileAction.SKIPPED,
                    message=f"远端目录已存在文件，按 SHA1匹配命中，按配置跳过 (id={existing.get('id')}, pickcode={existing.get('pickcode')})",
                    file_sha1=file_sha1,
                    remote_file_id=str(existing.get('id') or '') or None,
                    remote_pickcode=existing.get('pickcode'),
                    remote_dir_id=context.remote_dir_id,
                    remote_dir_path=context.remote_dir_path,
                )

        file_sha1 = self._ensure_sha1(candidate, file_sha1)
        range_reader = build_range_hash_reader(candidate.absolute_path)

        if upload_mode != UploadMode.MULTIPART_ONLY:
            init_resp = self.gateway.fast_upload_init(
                filename=candidate.absolute_path.name,
                filesize=candidate.size,
                filesha1=file_sha1,
                pid=context.remote_dir_id,
                read_range_hash=range_reader,
            )
            if init_resp.get('reuse'):
                data = init_resp.get('data', {})
                remote_file_id = str(data.get('file_id') or '') or None
                remote_pickcode = data.get('pickcode')
                self._store_uploaded_file(
                    context=context,
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
                    remote_dir_id=context.remote_dir_id,
                    remote_dir_path=context.remote_dir_path,
                )
            if upload_mode == UploadMode.FAST_ONLY:
                return UploadResult(
                    action=FileAction.SKIPPED,
                    message='未命中秒传，按配置跳过',
                    file_sha1=file_sha1,
                    remote_dir_id=context.remote_dir_id,
                    remote_dir_path=context.remote_dir_path,
                )

        response = self.gateway.multipart_upload(
            file_path=candidate.absolute_path,
            pid=context.remote_dir_id,
            filename=candidate.absolute_path.name,
            partsize=self.default_part_size_mb * 1024 * 1024,
            log=log,
            is_cancel_requested=is_cancel_requested,
        )
        data = response.get('data', response)
        remote_file_id = str(data.get('file_id') or '') or None
        remote_pickcode = data.get('pickcode') or data.get('pick_code')
        file_sha1 = response.get('filesha1') or file_sha1
        self._store_uploaded_file(
            context=context,
            filename=candidate.absolute_path.name,
            file_sha1=file_sha1,
            size=candidate.size,
            remote_file_id=remote_file_id,
            remote_pickcode=remote_pickcode,
        )
        action = FileAction.FAST_UPLOADED if response.get('reuse') else FileAction.MULTIPART_UPLOADED
        message = 'Open 链路命中秒传' if response.get('reuse') else 'Open 分片上传完成'
        return UploadResult(
            action=action,
            message=message,
            file_sha1=file_sha1,
            remote_file_id=remote_file_id,
            remote_pickcode=remote_pickcode,
            remote_dir_id=context.remote_dir_id,
            remote_dir_path=context.remote_dir_path,
        )

    @staticmethod
    def resolve_remote_dir_path(remote_root: str, candidate: LocalFileCandidate) -> str:
        remote_root_path = PurePosixPath(remote_root)
        remote_dir = remote_root_path.joinpath(*candidate.relative_path.parts[:-1]) if candidate.relative_path.parts[:-1] else remote_root_path
        return remote_dir.as_posix()
