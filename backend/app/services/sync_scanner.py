"""本地目录扫描与后缀过滤逻辑。"""

import fnmatch
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class LocalFileCandidate:
    """待同步的本地文件。"""

    absolute_path: Path
    relative_path: Path
    suffix: str
    size: int


def normalize_suffixes(suffix_rules: list[str]) -> set[str]:
    """规范化后缀规则。"""

    result = set()
    for item in suffix_rules:
        item = item.strip().lower()
        if not item:
            continue
        if not item.startswith("."):
            item = f".{item}"
        result.add(item)
    return result


def should_include_file(path: Path, suffix_rules: list[str], exclude_rules: list[str]) -> bool:
    """判断文件是否应纳入同步。"""

    suffixes = normalize_suffixes(suffix_rules)
    if suffixes and path.suffix.lower() not in suffixes:
        return False
    relative_text = path.as_posix()
    for pattern in exclude_rules:
        pattern = pattern.strip()
        if pattern and fnmatch.fnmatch(relative_text, pattern):
            return False
    return True


def scan_local_files(local_root: Path, suffix_rules: list[str], exclude_rules: list[str]) -> list[LocalFileCandidate]:
    """扫描本地目录并返回符合规则的文件。"""

    results: list[LocalFileCandidate] = []
    for path in sorted(local_root.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(local_root)
        if not should_include_file(relative_path, suffix_rules, exclude_rules):
            continue
        results.append(
            LocalFileCandidate(
                absolute_path=path,
                relative_path=relative_path,
                suffix=path.suffix.lower(),
                size=path.stat().st_size,
            )
        )
    return results


def calc_sha1(file_path: Path) -> str:
    """计算整文件 SHA1。"""

    digest = hashlib.sha1()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def build_range_hash_reader(file_path: Path) -> Callable[[str], str]:
    """构造 115 秒传区间哈希回调。"""

    def read_range_hash(range_str: str) -> str:
        start, end = map(int, range_str.split("-"))
        digest = hashlib.sha1()
        with file_path.open("rb") as handle:
            handle.seek(start)
            digest.update(handle.read(end - start + 1))
        return digest.hexdigest().upper()

    return read_range_hash
