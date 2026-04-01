"""同步源 Schema 测试。"""

from app.models.enums import UploadMode
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
    )
    assert payload.remote_path == "/sync/root"
    assert payload.suffix_rules == [".mkv", ".mp4"]
