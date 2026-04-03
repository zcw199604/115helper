"""同步源 Schema 测试。"""

from app.models.enums import DuplicateCheckMode, UploadFlowMode, UploadMode
from app.schemas.source import SourceCreate


def test_source_create_normalization() -> None:
    payload = SourceCreate(
        name='demo',
        local_path='/tmp',
        remote_path='sync/root/',
        upload_mode=UploadMode.FAST_ONLY,
        suffix_rules=['mkv', '.MP4'],
        exclude_rules=[],
        enabled=True,
        duplicate_check_mode=DuplicateCheckMode.SHA1,
        force_refresh_remote_cache=True,
    )
    assert payload.remote_path == '/sync/root'
    assert payload.suffix_rules == ['.mkv', '.mp4']
    assert payload.force_refresh_remote_cache is True
    assert payload.upload_flow_mode == UploadFlowMode.PLUGIN_ALIGNED


def test_source_create_duplicate_mode() -> None:
    payload = SourceCreate(
        name='demo',
        local_path='/tmp',
        remote_path='/sync',
        upload_mode=UploadMode.FAST_ONLY,
        upload_flow_mode=UploadFlowMode.BATCH_CACHED,
        suffix_rules=[],
        exclude_rules=[],
        enabled=True,
        duplicate_check_mode=DuplicateCheckMode.NAME,
    )
    assert payload.duplicate_check_mode == DuplicateCheckMode.NAME
    assert payload.upload_flow_mode == UploadFlowMode.BATCH_CACHED
