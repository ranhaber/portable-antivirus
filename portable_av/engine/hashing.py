from __future__ import annotations

import hashlib
from pathlib import Path


def hash_file(path: Path, max_size_bytes: int) -> str | None:
    if path.stat().st_size > max_size_bytes:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
