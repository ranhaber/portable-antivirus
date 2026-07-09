from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class EngineResult:
    engine: str
    clean: bool
    signature: str | None
    raw_output: str
    timed_out: bool = False
    error: str | None = None


class MalwareEngineAdapter(Protocol):
    async def scan_file(self, path: Path, timeout_sec: int) -> EngineResult: ...
