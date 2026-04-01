"""同步扫描相关测试。"""

from pathlib import Path

from app.services.sync_scanner import normalize_suffixes, scan_local_files, should_include_file


def test_normalize_suffixes() -> None:
    assert normalize_suffixes(["mp4", ".MKV", ""]) == {".mp4", ".mkv"}


def test_should_include_file_case_insensitive() -> None:
    assert should_include_file(Path("demo/Movie.MKV"), [".mkv"], []) is True
    assert should_include_file(Path("demo/Movie.txt"), [".mkv"], []) is False


def test_scan_local_files_filters(tmp_path: Path) -> None:
    (tmp_path / "A.MKV").write_text("1", encoding="utf-8")
    (tmp_path / "B.txt").write_text("2", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "C.mp4").write_text("3", encoding="utf-8")

    files = scan_local_files(tmp_path, [".mkv", ".mp4"], ["sub/*"])
    assert [item.relative_path.as_posix() for item in files] == ["A.MKV"]
