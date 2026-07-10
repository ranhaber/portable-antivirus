# Low-Level Design (LLD)

## Portable Antivirus Appliance

| Field | Value |
|---|---|
| **Document ID** | LLD-PAV-001 |
| **Version** | 0.6 |
| **Date** | 2026-07-10 |
| **Status** | Initial detailed design draft |
| **Source Requirements** | `SRS.md` v1.1 |
| **Source Architecture** | `HLD.md` v1.1 |
| **Target Hardware** | Radxa Zero 3W, 1 GB LPDDR4, 32 GB microSD, Waveshare Zero LCD HAT (A) |
| **Target OS** | Armbian Ubuntu 24.04 Noble Minimal (CLI), vendor kernel 6.1.115 |

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Design Scope](#2-design-scope)
3. [Runtime Process Model](#3-runtime-process-model)
4. [Python Package Layout](#4-python-package-layout)
5. [Common Data Types](#5-common-data-types)
6. [Configuration Design](#6-configuration-design)
7. [API Application Design](#7-api-application-design)
8. [Event Bus and WebSocket Design](#8-event-bus-and-websocket-design)
9. [Scan Engine Design](#9-scan-engine-design)
10. [Mount Manager Design](#10-mount-manager-design)
11. [Persistence Design](#11-persistence-design)
12. [Report Writer Design](#12-report-writer-design)
13. [Display Manager Design](#13-display-manager-design)
14. [Update Manager Design](#14-update-manager-design)
15. [Error Handling and Logging](#15-error-handling-and-logging)
16. [Security Implementation Details](#16-security-implementation-details)
17. [Testing Strategy](#17-testing-strategy)
18. [Implementation Notes by Milestone](#18-implementation-notes-by-milestone)
19. [Open Items](#19-open-items)
20. [Traceability](#20-traceability)
21. [Document History](#21-document-history)

---

## 1. Purpose

This document defines the low-level design for the Portable Antivirus Appliance. It expands the HLD into concrete Python modules, public class/function contracts, state transitions, request/response schemas, persistence methods, and service interactions.

The LLD is the input to the implementation plan. It intentionally avoids task sequencing and estimates except where milestone constraints affect technical design.

---

## 2. Design Scope

### 2.1 In Scope for v1

- Read-only removable media detection and mounting.
- Quick Scan and Full Scan.
- ClamAV scanning through `clamdscan` when viable, with `clamscan` fallback.
- YARA scanning with locally installed rules.
- ClamAV built-in archive scanning only.
- Scan progress events for displays, Web UI, REST clients, and WebSocket clients.
- Threat prompt behavior: continue, stop, details.
- TXT and HTML report generation.
- SQLite scan history.
- Local three-display UI and two-button input.
- LAN REST API and WebSocket.
- Manual or scheduled signature update.

### 2.2 Out of Scope for v1

- Deep Scan.
- Custom recursive archive extraction.
- Quarantine or delete actions on source media.
- Powered USB HDD support.
- Wi-Fi access point onboarding UI.
- Cloud upload, telemetry, or remote threat analysis.
- Multi-scan concurrency.

---

## 3. Runtime Process Model

### 3.1 Processes

| Process | systemd Unit | User | Responsibility |
|---|---|---|---|
| Engine/API | `portable-av-engine.service` | `portable-av` | FastAPI app, scan controller, event bus, history, reports |
| Display | `portable-av-display.service` | `portable-av` | SPI LCD rendering, button handling, WebSocket subscription |
| Mount helper | `portable-av-mount@.service` | `root` for mount operation | Validate device, mount read-only, notify engine |
| ClamAV daemon | `clamav-daemon.service` | distro default | Keep signatures loaded if memory allows |
| FreshClam | `clamav-freshclam.service` / timer | distro default | Signature updates |

### 3.2 Startup Ordering

1. OS boots from 32 GB microSD.
2. `portable-av-engine.service` starts after network target and local filesystem readiness.
3. Engine loads config, opens SQLite, initializes event bus, and enters `IDLE`.
4. `portable-av-display.service` starts after engine and connects to `ws://127.0.0.1:8080/api/v1/scan/events`.
5. Mount helper units are triggered only by `udev` events.

### 3.3 Failure Independence

- Engine remains operational if display service fails.
- Display service reconnects if engine restarts.
- Mount helper does not depend on the display service.
- Web UI is observational/control surface only; detection must work without a connected browser.

---

## 4. Python Package Layout

```text
portable_av/
  __init__.py
  api/
    __init__.py
    app.py
    auth.py
    dependencies.py
    routes_config.py
    routes_drive.py
    routes_history.py
    routes_scan.py
    routes_status.py
    schemas.py
    websocket.py
  common/
    __init__.py
    config.py
    errors.py
    logging.py
    paths.py
    time.py
  display/
    __init__.py
    buttons.py
    display_manager.py
    lcd_hat_driver.py
    screens.py
    ws_client.py
  engine/
    __init__.py
    clamav_adapter.py
    event_bus.py
    file_enumerator.py
    hashing.py
    progress.py
    scan_controller.py
    scan_models.py
    yara_adapter.py
  history/
    __init__.py
    db.py
    models.py
    repository.py
  mount/
    __init__.py
    device_detector.py
    filesystem_info.py
    mount_manager.py
    notify_engine.py
  reports/
    __init__.py
    report_writer.py
    templates/
      report.html.j2
      report.txt.j2
  update/
    __init__.py
    freshclam_runner.py
    yara_rules.py
```

### 4.1 Import Direction Rules

- `api` may depend on `engine`, `history`, `mount`, `update`, and `common`.
- `engine` may depend on `history`, `reports`, and `common`.
- `display` talks to engine only through REST/WebSocket schemas, not direct imports from `engine`.
- `mount` notifies engine through localhost HTTP, not direct database writes.
- `common` must not import from application feature packages.

---

## 5. Common Data Types

### 5.1 Enumerations

```python
from enum import StrEnum

class ScanMode(StrEnum):
    QUICK = "quick"
    FULL = "full"

class ScanState(StrEnum):
    BOOT = "boot"
    IDLE = "idle"
    MOUNTED = "mounted"
    MENU = "menu"
    SCANNING = "scanning"
    THREAT_PROMPT = "threat_prompt"
    COMPLETE = "complete"
    ERROR = "error"

class ScanStage(StrEnum):
    ENUMERATING = "enumerating"
    HASHING = "hashing"
    CLAMAV = "clamav"
    YARA = "yara"
    REPORTING = "reporting"
    COMPLETE = "complete"

class ScanStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class ThreatAction(StrEnum):
    PENDING = "pending"
    CONTINUE = "continue"
    STOP = "stop"
    DETAILS = "details"
```

### 5.2 Core Models

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

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
```

### 5.3 Scan IDs

`scan_id` format:

```text
YYYYMMDD-HHMMSS-<4-char random suffix>
```

Example:

```text
20260709-231842-a3f7
```

This format sorts chronologically while avoiding collision after rapid retry.

---

## 6. Configuration Design

### 6.1 File Location

Configuration lives at:

```text
/etc/portable-av/config.json
```

The engine reads configuration on startup and after authenticated `PUT /api/v1/config`.

### 6.2 Pydantic Models

```python
from pydantic import BaseModel, Field

class ApiConfig(BaseModel):
    bind_host: str = "0.0.0.0"
    bind_port: int = 8080
    auth_token_hash: str
    allow_unauthenticated_read: bool = False

class ScanConfig(BaseModel):
    default_mode: ScanMode = ScanMode.QUICK
    clamav_mode: str = Field(default="clamd", pattern="^(clamd|clamscan)$")
    max_file_size_bytes: int = 104_857_600
    per_file_timeout_sec: int = 120
    yara_enabled: bool = True
    yara_max_file_size_bytes: int = 52_428_800
    hash_max_file_size_bytes: int = 104_857_600

class StorageConfig(BaseModel):
    warn_percent: int = 90
    block_percent: int = 95

class DisplayConfig(BaseModel):
    refresh_hz_idle: float = 0.5
    refresh_hz_scanning: float = 2.0
    devices: list[dict] = []

class UpdatesConfig(BaseModel):
    freshclam_schedule: str = "03:00"

class AppConfig(BaseModel):
    version: int = 1
    api: ApiConfig
    scan: ScanConfig = ScanConfig()
    display: DisplayConfig = DisplayConfig()
    storage: StorageConfig = StorageConfig()
    updates: UpdatesConfig = UpdatesConfig()
```

### 6.3 Config Update Rules

- Config writes are atomic: write temp file, fsync, then rename.
- Invalid config returns HTTP 422 and does not modify the active file.
- Changing API bind host or port requires service restart.
- Scan limit changes apply to the next scan, not an active scan.
- Display device mappings are considered provisional until Milestone 1 hardware validation.

---

## 7. API Application Design

### 7.1 Application Factory

```python
def create_app(config_path: Path = DEFAULT_CONFIG_PATH) -> FastAPI:
    ...
```

Responsibilities:

- Load config.
- Initialize logging.
- Open SQLite connection pool/factory.
- Create singleton `EventBus`.
- Create singleton `ScanController`.
- Register routers and WebSocket endpoint.

### 7.2 Dependency Providers

```python
def get_config() -> AppConfig: ...
def get_scan_controller() -> ScanController: ...
def get_history_repository() -> HistoryRepository: ...
def require_write_auth(...) -> AuthPrincipal: ...
def optional_read_auth(...) -> AuthPrincipal | None: ...
```

### 7.3 REST Schemas

```python
class StartScanRequest(BaseModel):
    mode: ScanMode

class StartScanResponse(BaseModel):
    scan_id: str
    state: ScanState

class StatusResponse(BaseModel):
    state: ScanState
    active_scan_id: str | None
    drive: DriveInfoResponse | None
    version: str
    uptime_sec: int

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
```

### 7.4 Endpoint Behavior

| Method | Path | Handler | Notes |
|---|---|---|---|
| GET | `/api/v1/status` | `routes_status.get_status` | Read auth optional by config |
| GET | `/api/v1/drive` | `routes_drive.get_drive` | Returns 404 if no mounted drive |
| POST | `/api/v1/scan` | `routes_scan.start_scan` | 409 if no drive or scan active |
| DELETE | `/api/v1/scan` | `routes_scan.cancel_scan` | Idempotent cancel request |
| GET | `/api/v1/scan/progress` | `routes_scan.get_progress` | Snapshot from controller |
| POST | `/api/v1/scan/threat-action` | `routes_scan.threat_action` | Continue/stop/details during prompt |
| GET | `/api/v1/history` | `routes_history.list_scans` | Pagination required |
| GET | `/api/v1/history/{scan_id}` | `routes_history.get_scan` | Includes detections |
| GET | `/api/v1/history/{scan_id}/report.txt` | `routes_history.get_txt_report` | File response |
| GET | `/api/v1/history/{scan_id}/report.html` | `routes_history.get_html_report` | File response |
| POST | `/api/v1/update/clamav` | `routes_config.update_clamav` | Write auth required |
| POST | `/api/v1/update/yara` | `routes_config.update_yara` | Write auth required |
| GET | `/api/v1/config` | `routes_config.get_config` | Redacts token hash |
| PUT | `/api/v1/config` | `routes_config.put_config` | Write auth required |

### 7.5 HTTP Error Mapping

| Exception | HTTP Status |
|---|---|
| `NoDriveMountedError` | 409 |
| `ScanAlreadyRunningError` | 409 |
| `InvalidStateTransitionError` | 409 |
| `ScanNotFoundError` | 404 |
| `UnauthorizedError` | 401 |
| `ForbiddenError` | 403 |
| `ConfigValidationError` | 422 |
| `StorageThresholdExceededError` | 507 |

---

## 8. Event Bus and WebSocket Design

### 8.1 Event Model

```python
class EventEnvelope(BaseModel):
    type: str
    timestamp: datetime
    sequence: int
    payload: dict
```

`sequence` is process-local and monotonic. It helps display and WebSocket clients ignore stale reconnect messages.

### 8.2 Event Types

| Type | Payload |
|---|---|
| `system_status` | `StatusResponse` |
| `drive_mounted` | `DriveInfoResponse` |
| `drive_removed` | `{ "device": str }` |
| `scan_started` | `{ "scan_id": str, "mode": str }` |
| `scan_progress` | `ProgressResponse` |
| `stage_changed` | `{ "scan_id": str, "stage": str }` |
| `threat_detected` | Detection fields plus scan ID |
| `scan_cancelled` | `{ "scan_id": str }` |
| `scan_completed` | Final progress summary |
| `scan_error` | Error code and message |

### 8.3 Event Bus Interface

```python
class EventBus:
    async def publish(self, event_type: str, payload: BaseModel | dict) -> None: ...
    async def subscribe(self) -> AsyncIterator[EventEnvelope]: ...
    def latest_snapshot(self) -> EventEnvelope | None: ...
```

Implementation uses an in-process `asyncio.Queue` per subscriber. Slow subscribers are disconnected after queue overflow to protect the scan engine.

---

## 9. Scan Engine Design

### 9.1 ScanController Public Interface

```python
class ScanController:
    async def set_drive(self, drive: DriveInfo | None) -> None: ...
    async def start_scan(self, mode: ScanMode, requested_by: str) -> str: ...
    async def cancel_scan(self) -> None: ...
    async def handle_threat_action(self, action: ThreatAction) -> None: ...
    def get_status(self) -> EngineStatus: ...
    def get_progress(self) -> ScanProgress: ...
```

### 9.2 State Ownership

`ScanController` is the only module allowed to mutate engine state.

State is protected by an `asyncio.Lock`. Long-running subprocess and file scan work happens outside the lock, while state changes and progress snapshots happen inside short critical sections.

### 9.3 Start Scan Preconditions

`start_scan()` validates:

- Current state is `MOUNTED`, `MENU`, or `COMPLETE`.
- A drive is mounted.
- No active scan task exists.
- Internal storage is below block threshold.
- Requested mode is `quick` or `full`.

Failure raises a typed exception mapped by the API layer.

### 9.4 Pipeline

```text
start_scan
  -> create scan row
  -> enumerate files
  -> update total count if known
  -> for each FileCandidate
       -> enforce size limits
       -> hash if configured/needed
       -> run ClamAV
       -> run YARA if enabled and eligible
       -> record detections
       -> publish progress
       -> if detection: enter THREAT_PROMPT and wait
  -> write reports
  -> mark scan completed/cancelled/failed
```

### 9.5 Quick Scan Filter

```python
QUICK_SCAN_EXTENSIONS = {
    "exe", "dll", "sys", "scr", "com", "msi", "cab", "elf", "so", "bin", "apk", "dmg", "pkg",
    "ps1", "vbs", "js", "jse", "wsf", "bat", "cmd", "sh", "py", "pl", "rb",
    "doc", "docx", "docm", "xls", "xlsx", "xlsm", "ppt", "pptx", "pptm", "odt", "ods", "odp", "rtf",
    "zip", "7z", "rar", "tar", "gz", "bz2", "xz", "iso",
}
```

Files without one of these extensions are skipped in Quick Scan. Full Scan includes every regular file subject to configured file size and timeout limits.

### 9.6 File Enumerator

```python
class FileEnumerator:
    def enumerate(self, root: Path, mode: ScanMode) -> Iterator[FileCandidate]: ...
```

Rules:

- Never follows symlinks.
- Skips device files, sockets, FIFOs, and directories that cannot be read.
- Emits warnings to scan events/report for skipped paths.
- Uses `os.scandir()` for low overhead on the 1 GB RAM target.
- Does not build a full list in memory unless a count pass is explicitly enabled.

### 9.7 ClamAV Adapter

```python
class ClamAvAdapter:
    async def scan_file(self, path: Path, timeout_sec: int) -> EngineResult: ...
    async def healthcheck(self) -> EngineHealth: ...
```

Modes:

- `clamd`: call `clamdscan --no-summary --fdpass <path>` or equivalent supported by target packaging.
- `clamscan`: call `clamscan --no-summary <path>` as fallback.

Result parsing maps ClamAV output to:

```python
class EngineResult(BaseModel):
    engine: str
    clean: bool
    signature: str | None
    raw_output: str
    timed_out: bool = False
    error: str | None = None
```

### 9.8 YARA Adapter

```python
class YaraAdapter:
    def load_rules(self, rules_dir: Path) -> None: ...
    async def scan_file(self, path: Path, timeout_sec: int) -> list[EngineResult]: ...
```

Rules:

- Compile all `*.yar` and `*.yara`.
- Keep last known-good compiled ruleset if reload fails.
- Skip files larger than `yara_max_file_size_bytes`.
- Report compile errors to history and event bus.

### 9.9 Threat Prompt Handling

When any engine reports a detection:

1. Detection is inserted into SQLite immediately.
2. `threat_detected` event is published.
3. State changes to `THREAT_PROMPT`.
4. Pipeline awaits operator action through an `asyncio.Event`.
5. `continue` resumes scanning.
6. `stop` finalizes scan with status `completed` and threat count.
7. `details` emits display/API detail event and remains in `THREAT_PROMPT`.

Source media is never modified.

---

## 10. Mount Manager Design

### 10.1 udev Trigger

`udev` rule starts:

```text
portable-av-mount@<escaped-device>.service
```

The unit passes the block device path to:

```text
/opt/portable-av/venv/bin/python -m portable_av.mount.mount_manager --device /dev/sdX1
```

### 10.2 MountManager Interface

```python
class MountManager:
    def inspect_device(self, device: str) -> FilesystemInfo: ...
    def mount_readonly(self, device: str) -> DriveInfo: ...
    def unmount(self, mount_path: Path) -> None: ...
```

### 10.3 Read-Only Mount Flags

Common flags:

```text
ro,nosuid,nodev,noexec
```

Filesystem-specific command examples:

```text
mount -t vfat -o ro,nosuid,nodev,noexec /dev/sda1 /mnt/portable-av/<id>
mount -t exfat -o ro,nosuid,nodev,noexec /dev/sda1 /mnt/portable-av/<id>
ntfs-3g -o ro,nosuid,nodev,noexec /dev/sda1 /mnt/portable-av/<id>
mount -t ext4 -o ro,nosuid,nodev,noexec,noload /dev/sda1 /mnt/portable-av/<id>
```

### 10.4 Engine Notification

Mount helper notifies the engine with an internal localhost endpoint:

```http
POST /api/v1/internal/drive
```

Payload:

```json
{
  "event": "mounted",
  "device": "/dev/sda1",
  "mount_path": "/mnt/portable-av/sda1-ABCD",
  "label": "USB",
  "uuid": "ABCD-1234",
  "filesystem": "exfat",
  "size_bytes": 32000000000,
  "readonly": true
}
```

This endpoint binds to localhost and uses an internal shared secret file readable only by root and `portable-av`.

---

## 11. Persistence Design

### 11.1 SQLite Access

SQLite file:

```text
/var/lib/portable-av/history.db
```

`history.db` provides:

```python
def connect(db_path: Path) -> sqlite3.Connection: ...
def migrate(conn: sqlite3.Connection) -> None: ...
```

Connection settings:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;
```

### 11.2 Repository Interface

```python
class HistoryRepository:
    def create_scan(self, scan: ScanRecordCreate) -> None: ...
    def update_scan_progress(self, scan_id: str, progress: ScanProgress) -> None: ...
    def finish_scan(self, scan_id: str, result: ScanFinish) -> None: ...
    def insert_detection(self, detection: DetectionRecordCreate) -> int: ...
    def insert_event(self, event: EventRecordCreate) -> None: ...
    def list_scans(self, limit: int, offset: int) -> list[ScanRecord]: ...
    def get_scan(self, scan_id: str) -> ScanRecord | None: ...
    def get_detections(self, scan_id: str) -> list[DetectionRecord]: ...
    def insert_signature_update(self, update: SignatureUpdateRecordCreate) -> None: ...
```

### 11.3 Transaction Rules

- Scan creation, detection insertion, and scan finalization are committed immediately.
- Progress updates may be throttled to once per second or every N files to reduce SD writes.
- Events table stores significant events only, not every progress tick.
- Report paths are written only after files are successfully generated.

### 11.4 Storage Thresholds

Before starting a scan:

1. Check free space under `/var/lib/portable-av/`.
2. If usage >= `warn_percent`, publish warning and allow scan.
3. If usage >= `block_percent`, reject scan with `StorageThresholdExceededError`.

History retention is storage-bounded. Automatic deletion policy is not enabled in v1 unless explicitly configured later.

---

## 12. Report Writer Design

### 12.1 Interface

```python
class ReportWriter:
    def write_reports(self, scan_id: str, output_dir: Path) -> ReportPaths: ...
```

Input data is read from `HistoryRepository` after scan finalization.

### 12.2 Output Paths

```text
/var/lib/portable-av/reports/<scan_id>/report.txt
/var/lib/portable-av/reports/<scan_id>/report.html
```

### 12.3 Report Contents

- Scan ID.
- Start/end timestamps.
- Scan mode.
- Device label, UUID, filesystem, size.
- Engine versions and signature timestamps.
- Files scanned.
- Bytes scanned.
- Files skipped with reasons.
- Threat count.
- Detections table with engine, signature, path, hash if available.
- Final status: clean, threats found, cancelled, failed.

Reports must not include secrets, API tokens, Wi-Fi passwords, or internal auth material.

---

## 13. Display Manager Design

### 13.1 Components

| Module | Responsibility |
|---|---|
| `display_manager.py` | Main process loop |
| `ws_client.py` | Connect/reconnect to engine event stream |
| `screens.py` | Render state into screen buffers |
| `lcd_hat_driver.py` | SPI/GPIO display operations |
| `buttons.py` | KEY1/KEY2 debounce and gesture mapping |

### 13.2 LcdHatDriver Interface

```python
class LcdHatDriver:
    def init(self) -> None: ...
    def clear(self, screen_id: str) -> None: ...
    def draw_image(self, screen_id: str, image: "Image") -> None: ...
    def set_backlight(self, screen_id: str, enabled: bool) -> None: ...
    def close(self) -> None: ...
```

`screen_id` values:

- `main`
- `aux_left`
- `aux_right`

### 13.3 Button Mapping

| Physical Input | Logical Event |
|---|---|
| KEY1 short press | `down` |
| KEY2 short press | `enter` |
| KEY2 long press | `back` |
| KEY2 double click | `cancel` |

Button events call REST endpoints. The display manager does not directly mutate scan state.

### 13.4 Rendering Rules

- Display refresh during scan is capped by `refresh_hz_scanning`.
- Identical frames are not redrawn.
- If WebSocket disconnects, main display shows reconnecting status while engine continues.
- If engine is unreachable for more than 10 seconds, display shows engine offline.

---

## 14. Update Manager Design

### 14.1 FreshClam Runner

```python
class FreshclamRunner:
    async def run_update(self, timeout_sec: int = 900) -> SignatureUpdateResult: ...
```

Behavior:

- Runs `freshclam`.
- Captures exit code and output.
- Inserts `signature_updates` row.
- Publishes update success/failure event.

### 14.2 YARA Rules

```python
class YaraRulesManager:
    def install_rule_file(self, filename: str, content: bytes) -> None: ...
    def validate_rules(self) -> YaraValidationResult: ...
    def activate_rules(self) -> None: ...
```

Rules are written to a staging directory first. Activation happens only after successful compilation.

---

## 15. Error Handling and Logging

### 15.1 Error Base Classes

```python
class PortableAvError(Exception):
    code: str
    user_message: str
    detail: str | None

class RecoverableError(PortableAvError):
    pass

class FatalScanError(PortableAvError):
    pass
```

### 15.2 Log Locations

| Log | Location |
|---|---|
| Engine service | journald + `/var/log/portable-av/engine.log` if file logging enabled |
| Display service | journald + `/var/log/portable-av/display.log` if file logging enabled |
| Mount helper | journald |
| Update actions | SQLite `signature_updates` and journald |

### 15.3 Logging Rules

- Log scan lifecycle and authentication attempts.
- Do not log API tokens, Wi-Fi passwords, or full config dumps.
- Log full file paths from scanned media in reports/history because they are part of scan evidence.
- Throttle repeated per-file warnings to avoid filling the microSD.

---

## 16. Security Implementation Details

### 16.1 Privilege Boundaries

- Engine/API runs as `portable-av`.
- Display service runs as `portable-av` with `gpio` and `spi` supplemental groups.
- Mount helper uses root only for mount/unmount work.
- Scanned files are never executed.

### 16.2 API Authentication

- Write endpoints require bearer token.
- Token is stored as a bcrypt or Argon2 hash in config.
- `GET /api/v1/config` redacts the hash.
- Internal mount callback uses a separate local secret and is not exposed on LAN.

### 16.3 Filesystem Safety

- External media is read-only.
- Mounts use `nosuid,nodev,noexec`.
- Scanner temporary files live under `/tmp/portable-av/` or configured temp directory.
- Temporary directory is created with mode `0700` for `portable-av`.

---

## 17. Testing Strategy

### 17.1 Unit Tests

| Area | Test Focus |
|---|---|
| Config | Validation, defaults, atomic write failure |
| File enumerator | Quick filter, symlink skipping, unreadable paths |
| ClamAV adapter | Output parsing, timeout handling |
| YARA adapter | Compile failure, match parsing, last-good rules |
| Scan controller | State transitions, cancel, threat prompt |
| Repository | Migrations, CRUD methods, transaction behavior |
| API routes | Auth, status codes, schema validation |

### 17.2 Integration Tests

- Scan EICAR from a read-only mounted test fixture.
- Generate TXT and HTML reports.
- Exercise WebSocket progress events.
- Simulate media removal during scan.
- Run `freshclam` failure path with network disabled.

### 17.3 Hardware Validation Tests

- Boot Armbian Ubuntu 24.04 Noble Minimal vendor kernel from 32 GB microSD.
- Enable SPI3 overlay.
- Draw test image on ST7789 main display.
- Draw test images on both ST7735S auxiliary displays.
- Verify KEY1/KEY2 GPIO events and debounce.
- Run display service for 30 minutes.

---

## 18. Implementation Notes by Milestone

### Milestone 1: Hardware Bring-Up

Implement only enough software to validate:

- OS boot.
- SSH access.
- SPI3 overlay.
- LCD HAT pin mapping.
- Button GPIO mapping.

Deliverable code may live in `tools/bringup/` before being folded into `portable_av.display`.

### Milestone 2: Display Service Skeleton

Implement:

- `LcdHatDriver`.
- `DisplayManager`.
- `WsClient` reconnect loop.
- Button event mapping to REST calls.

Use mocked scan events until Milestone 3 engine endpoints exist.

### Milestone 3: Headless Scan Prototype

Implement:

- FastAPI app.
- Scan controller.
- File enumerator.
- ClamAV adapter.
- YARA adapter.
- SQLite repository.
- Report writer.
- API/WebSocket progress.

Display integration is optional for this milestone.

### Milestone 4: Integrated Appliance Loop

Implement:

- End-to-end button-driven scan start/cancel.
- Threat prompt behavior.
- Display progress and threat states.
- Web UI hooks.
- Storage threshold enforcement.

---

## 19. Open Items

| ID | Item | Owner / Resolution Point |
|---|---|---|
| LLD-OPEN-001 | Final validated display pin map | Milestone 1 |
| LLD-OPEN-002 | Final ClamAV mode: `clamd` or `clamscan` | Milestone 3 benchmark |
| LLD-OPEN-003 | Whether external 3.3V regulator is required | Milestone 1 power validation |
| LLD-OPEN-004 | Exact Python GPIO library on vendor kernel | Milestone 1 |
| LLD-OPEN-005 | Whether progress pre-count is worth the extra enumeration pass | Milestone 3 |

### 19.1 Design Decisions Still Pending Sign-Off

The LLD is implementable as written. The items below are **defaults or placeholders** that need hardware validation or benchmark results before they are locked. None block starting Milestone 1 or the headless scan path in Milestone 3.

| Decision | Current LLD default | Sign-off trigger | Blocks if unresolved |
|---|---|---|---|
| Display pin map and SPI assignment | Provisional mapping in HLD §5.5.3; `display.devices[]` empty in config | Milestone 1 bring-up on Radxa + HAT | Display service (Milestone 2) |
| Python SPI/GPIO library | `spidev` + Radxa-compatible GPIO (library TBD) | Milestone 1 driver spike on vendor kernel 6.1.115 | `LcdHatDriver`, `buttons.py` |
| HAT 3.3V power | Board 3.3V rail assumed sufficient | Milestone 1 current/voltage check under full backlight | Enclosure/power BOM only |
| ClamAV execution mode | `clamav_mode: "clamd"` with `clamscan` fallback | Milestone 3 RAM/CPU benchmark on 1 GB target | Final `clamd.conf` tuning and service enablement |
| Scan progress total count | Stream enumeration; optional pre-count not specified | Milestone 3 UX vs memory trade-off on real media | Accurate `files_total` / percent on first file only |
| Threat meter segment count | 12 segments (HLD §12.4) | Milestone 2 visual review on 240×240 | Cosmetic only |

**Sign-off rule:** When a row is resolved, update `config.json` defaults, the relevant LLD section, and close the matching `LLD-OPEN-*` item in the table above.

### 19.2 Radxa Validation Notes (2026-07-10)

Headless Milestone 3 validation on Radxa Zero 3W:

| Item | Result |
|---|---|
| NTFS USB read-only mount | Works with `ntfs-3g` package installed |
| Mount flags | `ro,nosuid,nodev,noexec` via `mount_manager` |
| Internal drive callback | `POST /api/v1/internal/drive` → engine state + WebSocket `drive_mounted` |
| Quick Scan on real media | 3 files, 67,930,968 bytes, 0 threats |
| WebSocket stages | `enumerating` → `clamav` → `hashing` → `yara` → `reporting` → `scan_completed` |
| Auto-mount deploy | `203/EXEC` fixed by env-file wrapper; `portable-av-mount@sda1.service` validated with `status=0/SUCCESS` |
| Removal wrapper | `/usr/local/bin/portable-av-mount --unmount --device /dev/sda1` updates API state to idle |
| Synthetic udev trigger | `udevadm trigger --action=add --subsystem-match=block --sysname-match=sda1` starts the mount service |
| Physical unplug/re-plug | Drive re-enumerated as `/dev/sdb1` and auto-mounted read-only with no manual command |

**udev device node:** the rule matches `sd[a-z][0-9]`, so re-plugged drives that re-enumerate under a different node (e.g. `sda1` → `sdb1`) still auto-mount correctly.

**OS dependency:** add `ntfs-3g` to Radxa package list for NTFS USB drives. FAT32/exFAT/ext4 paths use standard `mount`.

---

## 20. Traceability

| LLD Area | SRS Sections | HLD Sections |
|---|---|---|
| Runtime process model | SRS 7.3, 9 | HLD 6, 7 |
| Scan engine | SRS 3.2, 3.3, 3.10, 8 | HLD 7, 8, 9 |
| Mount manager | SRS 3.1, 9 | HLD 10, 15 |
| API | SRS 7.5, 9 | HLD 11 |
| Display manager | SRS 5, 6.2, 6.3 | HLD 12 |
| Persistence and reports | SRS 3.6, 7.4 | HLD 13 |
| Updates | SRS 3.7 | HLD 14 |
| Security | SRS 9 | HLD 15 |
| Testing | SRS 11 | HLD 17, 21 |

---

## 21. Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-07-09 | - | Initial LLD draft from SRS v1.1 and HLD v1.1 |
| 0.2 | 2026-07-09 | - | Added §19.1 design decisions pending sign-off |
| 0.3 | 2026-07-10 | - | Added §19.2 Radxa headless validation notes (mount, scan, WebSocket) |
| 0.4 | 2026-07-10 | - | Updated §19.2 with deploy install, systemd mount, and removal-wrapper validation |
| 0.5 | 2026-07-10 | - | Added synthetic udev trigger validation |
| 0.6 | 2026-07-10 | - | Physical unplug/re-plug auto-mount validated (`/dev/sdb1`) |

---

*End of Document*
