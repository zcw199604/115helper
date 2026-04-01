"""同步源 Schema 测试。"""

from app.models.enums import DuplicateCheckMode, UploadMode
from app.schemas.source import SourceCreate


def test_source_create_normalization() -> None:
    payload = SourceCreate(
        name="demo",
        local_path="/tmp",
        remote_path="sync/root/",
        upload_mode=UploadMode.FAST_ONLY,
        suffix_rules=["mkv", ".MP4"],
        exclude_rules=[],
        enabled=True,
        duplicate_check_mode=DuplicateCheckMode.SHA1,
    )
    assert payload.remote_path == "/sync/root"
    assert payload.suffix_rules == [".mkv", ".mp4"]


def test_source_create_duplicate_mode() -> None:
    payload = SourceCreate(
        name="demo",
        local_path="/tmp",
        remote_path="/sync",
        upload_mode=UploadMode.FAST_ONLY,
        suffix_rules=[],
        exclude_rules=[],
        enabled=True,
        duplicate_check_mode=DuplicateCheckMode.NAME,
    )
    assert payload.duplicate_check_mode == DuplicateCheckMode.NAME
