from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_FILESYSTEMS = frozenset({"vfat", "exfat", "ntfs", "ext2", "ext3", "ext4"})


@dataclass(frozen=True)
class FilesystemInfo:
    device: str
    filesystem: str
    label: str | None
    uuid: str | None
    size_bytes: int | None
    supported: bool
