from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from portable_av.common.config import AppConfig
from portable_av.common.domain import DriveInfo
from portable_av.common.errors import (
    InvalidStateTransitionError,
    NoDriveMountedError,
    ScanAlreadyRunningError,
    StorageThresholdExceededError,
)
from portable_av.common.models import ScanMode, ScanStage, ScanState, ScanStatus, ThreatAction
from portable_av.common.paths import AppPaths
from portable_av.common.time import generate_scan_id, utc_now
from portable_av.engine.clamav_adapter import ClamAvAdapter
from portable_av.engine.event_bus import EventBus
from portable_av.engine.file_enumerator import FileEnumerator
from portable_av.engine.hashing import hash_file
from portable_av.engine.progress import progress_percent
from portable_av.engine.scan_models import ScanProgress
from portable_av.engine.yara_adapter import YaraAdapter
from portable_av.history.models import DetectionRecordCreate, EventRecordCreate, ScanFinish, ScanRecordCreate
from portable_av.history.repository import HistoryRepository
from portable_av.reports.report_writer import ReportWriter


@dataclass
class EngineStatus:
    state: ScanState
    active_scan_id: str | None
    drive: DriveInfo | None
    now: datetime


class ScanController:
    """Owns engine state transitions and scan orchestration."""

    def __init__(
        self,
        *,
        config: AppConfig,
        paths: AppPaths,
        history_repository: HistoryRepository,
        event_bus: EventBus | None = None,
    ) -> None:
        self._config = config
        self._paths = paths
        self._history_repository = history_repository
        self._event_bus = event_bus
        self._state = ScanState.IDLE
        self._active_scan_id: str | None = None
        self._drive: DriveInfo | None = None
        self._progress = ScanProgress(
            scan_id=None,
            state=ScanState.IDLE,
            stage=None,
            files_total=None,
            files_scanned=0,
            bytes_scanned=0,
            threats=0,
            current_file=None,
            progress_percent=None,
        )
        self._lock = asyncio.Lock()
        self._scan_task: asyncio.Task[None] | None = None
        self._cancel_requested = False
        self._threat_action: ThreatAction | None = None
        self._threat_action_event = asyncio.Event()
        self._enumerator = FileEnumerator()
        self._clamav = ClamAvAdapter(mode=config.scan.clamav_mode)
        self._yara = YaraAdapter(paths.yara_rules)
        self._report_writer = ReportWriter(
            templates_dir=Path(__file__).resolve().parent.parent / "reports" / "templates"
        )

    def get_status(self) -> EngineStatus:
        return EngineStatus(
            state=self._state,
            active_scan_id=self._active_scan_id,
            drive=self._drive,
            now=utc_now(),
        )

    def get_progress(self) -> ScanProgress:
        return self._progress

    async def set_drive(self, drive: DriveInfo | None) -> None:
        async with self._lock:
            if self._state == ScanState.SCANNING:
                return
            self._drive = drive
            self._state = ScanState.MOUNTED if drive else ScanState.IDLE
        await self._publish_progress()

    async def start_scan(
        self,
        mode: ScanMode,
        *,
        requested_by: str = "api",
        scan_root: Path | None = None,
    ) -> str:
        async with self._lock:
            if self._scan_task and not self._scan_task.done():
                raise ScanAlreadyRunningError()
            if self._state not in {ScanState.MOUNTED, ScanState.MENU, ScanState.COMPLETE} and scan_root is None:
                raise InvalidStateTransitionError(
                    user_message="Cannot start a scan in the current state."
                )
            root = scan_root or (self._drive.mount_path if self._drive else None)
            if root is None:
                raise NoDriveMountedError()
            self._check_storage_threshold()

            scan_id = generate_scan_id()
            self._active_scan_id = scan_id
            self._state = ScanState.SCANNING
            self._cancel_requested = False
            self._threat_action = None
            self._threat_action_event.clear()
            self._progress = ScanProgress(
                scan_id=scan_id,
                state=ScanState.SCANNING,
                stage=ScanStage.ENUMERATING,
                files_total=None,
                files_scanned=0,
                bytes_scanned=0,
                threats=0,
                current_file=None,
                progress_percent=None,
            )
            self._history_repository.create_scan(
                ScanRecordCreate(
                    scan_id=scan_id,
                    mode=mode,
                    device_label=self._drive.label if self._drive else None,
                    device_uuid=self._drive.uuid if self._drive else None,
                    filesystem=self._drive.filesystem if self._drive else None,
                )
            )
            self._history_repository.insert_event(
                EventRecordCreate(
                    scan_id=scan_id,
                    event_type="scan_started",
                    message=f"Scan started by {requested_by} in {mode.value} mode",
                )
            )
            self._scan_task = asyncio.create_task(self._run_scan(scan_id, mode, Path(root)))
            await self._publish("scan_started", {"scan_id": scan_id, "mode": mode.value})
            return scan_id

    async def cancel_scan(self) -> None:
        self._cancel_requested = True
        if self._state == ScanState.THREAT_PROMPT:
            self._threat_action = ThreatAction.STOP
            self._threat_action_event.set()
        if self._active_scan_id:
            await self._publish("scan_cancelled", {"scan_id": self._active_scan_id})

    async def handle_threat_action(self, action: ThreatAction) -> None:
        if self._state != ScanState.THREAT_PROMPT:
            raise InvalidStateTransitionError(
                user_message="No threat prompt is active."
            )
        self._threat_action = action
        self._threat_action_event.set()

    def _check_storage_threshold(self) -> None:
        usage = shutil.disk_usage(self._paths.data)
        used_percent = int((usage.used / usage.total) * 100)
        if used_percent >= self._config.storage.block_percent:
            raise StorageThresholdExceededError(
                detail=f"Storage usage is {used_percent}%"
            )

    async def _run_scan(self, scan_id: str, mode: ScanMode, root: Path) -> None:
        files_scanned = 0
        bytes_scanned = 0
        threats = 0
        skipped_large = 0
        status = ScanStatus.COMPLETED
        report_txt_path: str | None = None
        report_html_path: str | None = None

        try:
            await self._set_progress(stage=ScanStage.ENUMERATING, current_file=None)
            for candidate in self._enumerator.enumerate(root, mode):
                if self._cancel_requested:
                    status = ScanStatus.CANCELLED
                    break
                if candidate.size_bytes > self._config.scan.max_file_size_bytes:
                    skipped_large += 1
                    continue

                await self._set_progress(
                    stage=ScanStage.CLAMAV,
                    current_file=candidate.relative_path,
                    files_scanned=files_scanned,
                    bytes_scanned=bytes_scanned,
                    threats=threats,
                )
                clam_result = await self._clamav.scan_file(
                    candidate.path,
                    self._config.scan.per_file_timeout_sec,
                )
                if clam_result.timed_out:
                    self._history_repository.insert_event(
                        EventRecordCreate(
                            scan_id=scan_id,
                            event_type="file_skipped",
                            message=f"Timeout: {candidate.relative_path}",
                        )
                    )
                    continue

                file_hash = None
                if candidate.size_bytes <= self._config.scan.hash_max_file_size_bytes:
                    await self._set_progress(stage=ScanStage.HASHING, current_file=candidate.relative_path)
                    try:
                        file_hash = hash_file(
                            candidate.path,
                            self._config.scan.hash_max_file_size_bytes,
                        )
                    except OSError:
                        file_hash = None

                stop_scan = False
                if not clam_result.clean and clam_result.signature:
                    threats += 1
                    await self._record_detection(
                        scan_id,
                        engine="clamav",
                        signature=clam_result.signature,
                        file_path=candidate.relative_path,
                        sha256=file_hash,
                    )
                    if not await self._await_threat_action():
                        stop_scan = True

                if not stop_scan and self._config.scan.yara_enabled and candidate.size_bytes <= self._config.scan.yara_max_file_size_bytes:
                    await self._set_progress(stage=ScanStage.YARA, current_file=candidate.relative_path)
                    for yara_result in await self._yara.scan_file(
                        candidate.path,
                        self._config.scan.per_file_timeout_sec,
                    ):
                        if yara_result.clean or not yara_result.signature:
                            continue
                        threats += 1
                        await self._record_detection(
                            scan_id,
                            engine="yara",
                            signature=yara_result.signature,
                            file_path=candidate.relative_path,
                            sha256=file_hash,
                        )
                        if not await self._await_threat_action():
                            stop_scan = True
                            break

                if stop_scan:
                    break

                files_scanned += 1
                bytes_scanned += candidate.size_bytes
                if files_scanned % 10 == 0:
                    self._history_repository.update_scan_progress(
                        scan_id,
                        files_scanned=files_scanned,
                        bytes_scanned=bytes_scanned,
                        threat_count=threats,
                    )

            await self._set_progress(stage=ScanStage.REPORTING, current_file=None)
            report_dir = self._paths.reports / scan_id
            scan_record = self._history_repository.get_scan(scan_id) or {}
            scan_record.update(
                {
                    "files_scanned": files_scanned,
                    "bytes_scanned": bytes_scanned,
                    "threat_count": threats,
                    "status": status.value,
                }
            )
            detections = self._history_repository.get_detections(scan_id)
            report_paths = self._report_writer.write_reports(
                scan_id=scan_id,
                output_dir=report_dir,
                scan_record=scan_record,
                detections=detections,
            )
            report_txt_path = str(report_paths.txt_path)
            report_html_path = str(report_paths.html_path)
            if skipped_large:
                self._history_repository.insert_event(
                    EventRecordCreate(
                        scan_id=scan_id,
                        event_type="files_skipped",
                        message=f"Skipped {skipped_large} files over size limit",
                    )
                )
        except Exception as exc:
            status = ScanStatus.FAILED
            await self._publish("scan_error", {"scan_id": scan_id, "message": str(exc)})
            self._history_repository.insert_event(
                EventRecordCreate(
                    scan_id=scan_id,
                    event_type="scan_error",
                    message=str(exc),
                )
            )
        finally:
            self._history_repository.finish_scan(
                scan_id,
                ScanFinish(
                    status=status,
                    files_total=None,
                    files_scanned=files_scanned,
                    bytes_scanned=bytes_scanned,
                    threat_count=threats,
                    report_txt_path=report_txt_path,
                    report_html_path=report_html_path,
                ),
            )
            async with self._lock:
                self._state = ScanState.COMPLETE
                self._active_scan_id = None
                self._progress = ScanProgress(
                    scan_id=scan_id,
                    state=ScanState.COMPLETE,
                    stage=ScanStage.COMPLETE,
                    files_total=None,
                    files_scanned=files_scanned,
                    bytes_scanned=bytes_scanned,
                    threats=threats,
                    current_file=None,
                    progress_percent=None,
                )
            await self._publish(
                "scan_completed",
                {
                    "scan_id": scan_id,
                    "status": status.value,
                    "files_scanned": files_scanned,
                    "bytes_scanned": bytes_scanned,
                    "threats": threats,
                },
            )

    async def _record_detection(
        self,
        scan_id: str,
        *,
        engine: str,
        signature: str,
        file_path: str,
        sha256: str | None,
    ) -> None:
        self._history_repository.insert_detection(
            DetectionRecordCreate(
                scan_id=scan_id,
                engine=engine,
                signature=signature,
                file_path=file_path,
                sha256=sha256,
                action=ThreatAction.PENDING.value,
            )
        )
        self._history_repository.insert_event(
            EventRecordCreate(
                scan_id=scan_id,
                event_type="threat_detected",
                message=f"[{engine}] {signature} in {file_path}",
            )
        )
        await self._publish(
            "threat_detected",
            {
                "scan_id": scan_id,
                "engine": engine,
                "signature": signature,
                "file_path": file_path,
                "sha256": sha256,
            },
        )

    async def _await_threat_action(self) -> bool:
        while True:
            async with self._lock:
                self._state = ScanState.THREAT_PROMPT
                self._progress = ScanProgress(
                    scan_id=self._progress.scan_id,
                    state=ScanState.THREAT_PROMPT,
                    stage=self._progress.stage,
                    files_total=self._progress.files_total,
                    files_scanned=self._progress.files_scanned,
                    bytes_scanned=self._progress.bytes_scanned,
                    threats=self._progress.threats,
                    current_file=self._progress.current_file,
                    progress_percent=self._progress.progress_percent,
                )
            self._threat_action_event.clear()
            await self._threat_action_event.wait()
            action = self._threat_action or ThreatAction.STOP
            if action == ThreatAction.CONTINUE:
                async with self._lock:
                    self._state = ScanState.SCANNING
                return True
            if action == ThreatAction.DETAILS:
                continue
            return False

    async def _set_progress(
        self,
        *,
        stage: ScanStage,
        current_file: str | None,
        files_scanned: int | None = None,
        bytes_scanned: int | None = None,
        threats: int | None = None,
    ) -> None:
        previous_stage = self._progress.stage
        self._progress = ScanProgress(
            scan_id=self._progress.scan_id,
            state=ScanState.SCANNING,
            stage=stage,
            files_total=self._progress.files_total,
            files_scanned=files_scanned if files_scanned is not None else self._progress.files_scanned,
            bytes_scanned=bytes_scanned if bytes_scanned is not None else self._progress.bytes_scanned,
            threats=threats if threats is not None else self._progress.threats,
            current_file=current_file,
            progress_percent=progress_percent(
                files_scanned if files_scanned is not None else self._progress.files_scanned,
                self._progress.files_total,
            ),
        )
        await self._publish_progress()
        if previous_stage != stage:
            await self._publish(
                "stage_changed",
                {
                    "scan_id": self._progress.scan_id,
                    "stage": stage.value,
                },
            )

    async def _publish_progress(self) -> None:
        await self._publish("scan_progress", self._progress_payload())

    def _progress_payload(self) -> dict:
        return {
            "scan_id": self._progress.scan_id,
            "state": self._progress.state.value,
            "stage": self._progress.stage.value if self._progress.stage else None,
            "files_total": self._progress.files_total,
            "files_scanned": self._progress.files_scanned,
            "bytes_scanned": self._progress.bytes_scanned,
            "threats": self._progress.threats,
            "current_file": self._progress.current_file,
            "progress_percent": self._progress.progress_percent,
        }

    async def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(event_type, payload)
