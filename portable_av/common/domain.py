from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class DriveInfo:
    device: str
    mount_path: Path
    label: str | None
    uuid: str | None
    filesystem: str
    size_bytes: int | None
    readonly: bool


@dataclass(frozen=True)
class FileCandidate:
    path: Path
    relative_path: str
    size_bytes: int
    modified_at: datetime | None
    extension: str


@dataclass(frozen=True)
class Detection:
    engine: str
    signature: str
    file_path: str
    sha256: str | None
    detected_at: datetime
