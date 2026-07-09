from __future__ import annotations

from dataclasses import dataclass

from portable_av.common.models import ScanMode, ScanStatus


@dataclass(frozen=True)
class ScanRecordCreate:
    scan_id: str
    mode: ScanMode
    device_label: str | None
    device_uuid: str | None
    filesystem: str | None


@dataclass(frozen=True)
class ScanFinish:
    status: ScanStatus
    files_total: int | None
    files_scanned: int
    bytes_scanned: int
    threat_count: int
    report_txt_path: str | None
    report_html_path: str | None


@dataclass(frozen=True)
class DetectionRecordCreate:
    scan_id: str
    engine: str
    signature: str
    file_path: str
    sha256: str | None
    action: str


@dataclass(frozen=True)
class EventRecordCreate:
    scan_id: str | None
    event_type: str
    message: str
