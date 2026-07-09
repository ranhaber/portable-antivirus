from dataclasses import dataclass

from portable_av.common.models import ScanMode, ScanStage, ScanState


@dataclass
class ScanProgress:
    scan_id: str | None
    state: ScanState
    stage: ScanStage | None
    files_total: int | None
    files_scanned: int
    bytes_scanned: int
    threats: int
    current_file: str | None
    progress_percent: float | None
