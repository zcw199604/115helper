"""上传策略测试。"""

from pathlib import Path

from app.models.enums import FileAction, UploadMode
from app.services.sync_scanner import LocalFileCandidate, calc_sha1
from app.services.upload_strategy import UploadStrategyService


class FakeGateway:
    def __init__(self, existing: dict | None = None) -> None:
        self.existing = existing
        self.fast_called = False
        self.multipart_called = False

    def ensure_remote_dir(self, _remote_dir):
        return 100

    def find_existing_remote_file(self, *, pid: int, filename: str, filesize: int, filesha1: str):
        assert pid == 100
        assert filename
        assert filesize >= 0
        assert filesha1
        return self.existing

    def fast_upload_init(self, **_kwargs):
        self.fast_called = True
        return {"reuse": True, "data": {"file_id": "200", "pickcode": "pc200"}}

    def multipart_upload(self, **_kwargs):
        self.multipart_called = True
        return {"data": {"file_id": "300", "pickcode": "pc300"}}


def test_upload_candidate_skips_when_remote_exists(tmp_path: Path) -> None:
    file_path = tmp_path / "demo.mkv"
    file_path.write_bytes(b"hello world")
    candidate = LocalFileCandidate(
        absolute_path=file_path,
        relative_path=Path("demo.mkv"),
        suffix=".mkv",
        size=file_path.stat().st_size,
    )
    gateway = FakeGateway(existing={"id": "901", "pickcode": "pc901"})
    service = UploadStrategyService(gateway)

    result = service.upload_candidate(candidate, "/remote", UploadMode.FAST_THEN_MULTIPART, skip_existing_remote=True)

    assert result.action == FileAction.SKIPPED
    assert "防重复上传配置跳过" in result.message
    assert result.remote_file_id == "901"
    assert result.remote_pickcode == "pc901"
    assert result.file_sha1 == calc_sha1(file_path)
    assert gateway.fast_called is False
    assert gateway.multipart_called is False
