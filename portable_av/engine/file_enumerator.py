from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from portable_av.common.domain import FileCandidate
from portable_av.common.models import ScanMode

QUICK_SCAN_EXTENSIONS = {
    "exe", "dll", "sys", "scr", "com", "msi", "cab", "elf", "so", "bin", "apk", "dmg", "pkg",
    "ps1", "vbs", "js", "jse", "wsf", "bat", "cmd", "sh", "py", "pl", "rb",
    "doc", "docx", "docm", "xls", "xlsx", "xlsm", "ppt", "pptx", "pptm", "odt", "ods", "odp", "rtf",
    "zip", "7z", "rar", "tar", "gz", "bz2", "xz", "iso",
}


def extension_of(path: Path) -> str:
    return path.suffix.lstrip(".").lower()


def should_scan_file(path: Path, mode: ScanMode) -> bool:
    if not path.is_file():
        return False
    if mode == ScanMode.FULL:
        return True
    return extension_of(path) in QUICK_SCAN_EXTENSIONS


class FileEnumerator:
    def enumerate(self, root: Path, mode: ScanMode) -> Iterator[FileCandidate]:
        root = root.resolve()
        stack: list[Path] = [root]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            if entry.is_symlink():
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(Path(entry.path))
                                continue
                            if not entry.is_file(follow_symlinks=False):
                                continue
                            path = Path(entry.path)
                            if not should_scan_file(path, mode):
                                continue
                            stat = entry.stat(follow_symlinks=False)
                            modified_at = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                            yield FileCandidate(
                                path=path,
                                relative_path=str(path.relative_to(root)),
                                size_bytes=stat.st_size,
                                modified_at=modified_at,
                                extension=extension_of(path),
                            )
                        except OSError:
                            continue
            except OSError:
                continue
