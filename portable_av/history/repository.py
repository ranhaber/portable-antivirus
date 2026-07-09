from __future__ import annotations

import sqlite3
from pathlib import Path

from portable_av.common.time import utc_now
from portable_av.history.db import SCHEMA_SQL, SCHEMA_VERSION
from portable_av.history.models import (
    DetectionRecordCreate,
    EventRecordCreate,
    ScanFinish,
    ScanRecordCreate,
)


class HistoryRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.execute(
                """
                INSERT OR IGNORE INTO schema_migrations(version, applied_at)
                VALUES (?, ?)
                """,
                (SCHEMA_VERSION, utc_now().isoformat()),
            )
            conn.commit()

    def create_scan(self, scan: ScanRecordCreate) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scans (
                    scan_id, started_at, status, mode,
                    device_label, device_uuid, filesystem
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan.scan_id,
                    utc_now().isoformat(),
                    "running",
                    scan.mode.value,
                    scan.device_label,
                    scan.device_uuid,
                    scan.filesystem,
                ),
            )
            conn.commit()

    def update_scan_progress(
        self,
        scan_id: str,
        *,
        files_scanned: int,
        bytes_scanned: int,
        threat_count: int,
        files_total: int | None = None,
    ) -> None:
        with self._connect() as conn:
            if files_total is None:
                conn.execute(
                    """
                    UPDATE scans
                    SET files_scanned = ?, bytes_scanned = ?, threat_count = ?
                    WHERE scan_id = ?
                    """,
                    (files_scanned, bytes_scanned, threat_count, scan_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE scans
                    SET files_total = ?, files_scanned = ?, bytes_scanned = ?, threat_count = ?
                    WHERE scan_id = ?
                    """,
                    (files_total, files_scanned, bytes_scanned, threat_count, scan_id),
                )
            conn.commit()

    def finish_scan(self, scan_id: str, result: ScanFinish) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE scans
                SET ended_at = ?, status = ?, files_total = ?, files_scanned = ?,
                    bytes_scanned = ?, threat_count = ?,
                    report_txt_path = ?, report_html_path = ?
                WHERE scan_id = ?
                """,
                (
                    utc_now().isoformat(),
                    result.status.value,
                    result.files_total,
                    result.files_scanned,
                    result.bytes_scanned,
                    result.threat_count,
                    result.report_txt_path,
                    result.report_html_path,
                    scan_id,
                ),
            )
            conn.commit()

    def insert_detection(self, detection: DetectionRecordCreate) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO detections (
                    scan_id, engine, signature, file_path, sha256, detected_at, action
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    detection.scan_id,
                    detection.engine,
                    detection.signature,
                    detection.file_path,
                    detection.sha256,
                    utc_now().isoformat(),
                    detection.action,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def insert_event(self, event: EventRecordCreate) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO events (scan_id, event_type, message, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event.scan_id,
                    event.event_type,
                    event.message,
                    utc_now().isoformat(),
                ),
            )
            conn.commit()

    def get_scan(self, scan_id: str) -> dict | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM scans WHERE scan_id = ?",
                (scan_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_detections(self, scan_id: str) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM detections WHERE scan_id = ? ORDER BY id",
                (scan_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
