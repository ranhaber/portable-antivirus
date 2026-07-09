from pydantic import BaseModel

from portable_av.common.models import ScanMode, ScanState, ScanStage, ThreatAction


class DriveInfoResponse(BaseModel):
    device: str
    mount_path: str
    label: str | None
    uuid: str | None
    filesystem: str
    size_bytes: int | None
    readonly: bool


class StatusResponse(BaseModel):
    state: ScanState
    active_scan_id: str | None
    drive: DriveInfoResponse | None
    version: str
    uptime_sec: int


class StartScanRequest(BaseModel):
    mode: ScanMode


class StartScanResponse(BaseModel):
    scan_id: str
    state: ScanState


class ProgressResponse(BaseModel):
    scan_id: str | None
    state: ScanState
    stage: ScanStage | None
    files_total: int | None
    files_scanned: int
    bytes_scanned: int
    threats: int
    current_file: str | None
    progress_percent: float | None


class ThreatActionRequest(BaseModel):
    action: ThreatAction
