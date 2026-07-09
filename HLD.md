# High-Level Design (HLD)

## Portable Antivirus Appliance

| Field | Value |
|---|---|
| **Document ID** | HLD-PAV-001 |
| **Version** | 1.1 |
| **Date** | 2026-07-09 |
| **Status** | Complete — pending prototype hardware validation |
| **Source Requirements** | `SRS.md` v1.1 |
| **Target Hardware** | Radxa Zero 3W, 1 GB LPDDR4, 32 GB microSD, Waveshare Zero LCD HAT (A) |
| **Target OS** | Armbian Ubuntu 24.04 Noble Minimal (CLI), vendor kernel 6.1.115 |

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Design Goals](#2-design-goals)
3. [Confirmed Architecture Decisions](#3-confirmed-architecture-decisions)
4. [System Context](#4-system-context)
5. [Hardware Design](#5-hardware-design)
6. [Operating System Design](#6-operating-system-design)
7. [Software Architecture](#7-software-architecture)
8. [Data Flow](#8-data-flow)
9. [Scan Design](#9-scan-design)
10. [Mount Manager Design](#10-mount-manager-design)
11. [API Design](#11-api-design)
12. [Display Manager Design](#12-display-manager-design)
13. [Persistence Design](#13-persistence-design)
14. [Updates Design](#14-updates-design)
15. [Security Design](#15-security-design)
16. [Error Handling Design](#16-error-handling-design)
17. [Prototype Milestones](#17-prototype-milestones)
18. [Web UI Design](#18-web-ui-design-v1-scope)
19. [Deployment Design](#19-deployment-design)
20. [Risks and Mitigations](#20-risks-and-mitigations)
21. [Validation Checklist](#21-validation-checklist-prototype)
22. [Open Items](#22-open-items)
23. [Traceability](#23-traceability)
- [Appendix A: SQLite DDL](#appendix-a-sqlite-ddl-v1)
- [Appendix B: systemd Units](#appendix-b-systemd-unit-sketch)
- [Appendix C: Document History](#appendix-c-document-history)

---

## 1. Purpose

This document defines the high-level design for the Portable Antivirus Appliance. It translates the SRS into a practical system architecture covering hardware integration, OS setup, service boundaries, data flow, scan pipeline, API design, display handling, persistence, security, and prototype milestones.

The v1 design is intentionally conservative because the hardware is fixed to:

- Radxa Zero 3W with 1 GB LPDDR4.
- 32 GB microSD only.
- Waveshare Zero LCD HAT (A) / Triple IPS LCD HAT.
- No current sensor or live per-rail power measurement.
- No USB HDD support.
- Quick Scan and Full Scan only; Deep Scan is deferred to v2.

---

## 2. Design Goals

| ID | Goal |
|---|---|
| DG-001 | Scan USB flash drives, low-power portable SSDs, SD cards, and microSD cards without a host PC. |
| DG-002 | Mount all scanned media read-only. |
| DG-003 | Keep the scan engine headless and independent of the display manager, web UI, and API clients. |
| DG-004 | Run acceptably on 1 GB RAM by using a single active scan pipeline by default. |
| DG-005 | Use the Triple IPS LCD HAT for local operator feedback with a compact industrial UI adapted to 240×240 and 160×80 screens. |
| DG-006 | Provide REST and WebSocket interfaces for web UI and future Android app integration. |
| DG-007 | Store scan history and reports on the 32 GB microSD card. |

---

## 3. Confirmed Architecture Decisions

| Area | Decision |
|---|---|
| HLD scope | Full system HLD |
| Main language | Python 3 |
| API framework | FastAPI + Uvicorn |
| Display bring-up | Userspace SPI/GPIO driver first |
| Display HAT | Waveshare Zero LCD HAT (A): ST7789 240x240 + 2x ST7735S 160x80 |
| Scan engine | Headless Python service |
| ClamAV integration | Target `clamd` + `clamdscan`; benchmark fallback to `clamscan` |
| YARA | Enabled in v1 |
| Archive handling | ClamAV built-in archive scanning only; no custom recursive extraction |
| Wi-Fi | Client mode only for v1 |
| Web/API auth | Local-network token/password auth for config and scan control |
| History | SQLite metadata + TXT/HTML report files |
| USB mount handling | `udev` triggers + systemd mount manager |
| Scan concurrency | Benchmark-dependent; default design is one active file pipeline |
| Signature updates | `freshclam` for ClamAV; manual YARA rule copy/upload |
| Prototype priority | Display HAT works on Radxa, buttons work, simple status UI |

---

## 4. System Context

```
                 Local Operator
                       |
                       v
       +--------------------------------+
       | Triple IPS LCD HAT + Buttons   |
       +----------------+---------------+
                        |
                        v
+---------------------------------------------------------------+
|                    Portable AV Appliance                       |
|                                                               |
|  +------------------+      +-------------------------------+  |
|  | Display Manager  |<---->| FastAPI / WebSocket API       |  |
|  | userspace SPI    |      | local token auth              |  |
|  +------------------+      +---------------+---------------+  |
|                                           |                  |
|                                           v                  |
|  +------------------+      +-------------------------------+  |
|  | udev/systemd     |----->| Scan Engine                    |  |
|  | Mount Manager    |      | enumerate, hash, ClamAV, YARA  |  |
|  +------------------+      +---------------+---------------+  |
|                                           |                  |
|                              +------------+-----------+      |
|                              v                        v      |
|                      +---------------+        +--------------+|
|                      | SQLite        |        | TXT / HTML   ||
|                      | history.db    |        | reports      ||
|                      +---------------+        +--------------+|
|                                                               |
+----------------------+------------------------+---------------+
                       |                        |
                       v                        v
             Read-only removable media      Wi-Fi LAN
                                            Web UI / API client
```

---

## 5. Hardware Design

### 5.1 Compute Platform

| Component | Design |
|---|---|
| Board | Radxa Zero 3W |
| RAM | Fixed 1 GB LPDDR4 |
| Storage | Fixed 32 GB microSD card |
| OS | Armbian Ubuntu 24.04 Noble Minimal (CLI), vendor kernel 6.1.115 |
| Power input | USB-C 5V/3A recommended |
| Network | Onboard Wi-Fi in client mode |
| USB scan port | USB 3.0 host, adapted to user-accessible USB-A or USB-C port |

### 5.2 Display HAT

The v1 hardware uses the Waveshare Zero LCD HAT (A), sold as the Triple IPS LCD HAT.

| Screen | Controller | Resolution | Intended Role |
|---|---|---|---|
| Main | ST7789 | 240x240 | Task status, progress, alert |
| Aux 1 | ST7735S | 160x80 | Drive/status field TBD |
| Aux 2 | ST7735S | 160x80 | Security/status field TBD |

The HAT is a major integration item because it was designed for Raspberry Pi SPI/GPIO mappings. The Radxa Zero 3W exposes different GPIO alternate functions. The first prototype shall use userspace SPI/GPIO control to reduce kernel/device-tree complexity. If userspace SPI cannot meet refresh or stability requirements, a later HLD revision may introduce kernel framebuffer drivers or custom device-tree overlays.

### 5.3 Power Design

The appliance has no current sensor. It cannot directly measure display current or per-rail power consumption in software.

Estimated power budget:

| Mode | Estimated Power |
|---|---|
| Idle, displays on | About 4 W |
| Scanning USB flash drive | About 6-8 W |
| Scanning low-power portable SSD | About 8-10 W |

Design rules:

- Use a high-quality 5V/3A supply.
- Bench-test the 3.3V rail with the LCD HAT active.
- Add an external 3.3V regulator only if prototype testing shows voltage drop, resets, display flicker, or board instability.
- Do not support USB HDDs in v1.

### 5.4 Physical Input

The two HAT buttons are used for local operation.

| Input | Function |
|---|---|
| Button 1 | Down / next |
| Button 2 short press | Enter / confirm |
| Button 2 long press | Back |
| Button 2 double-click | Cancel active scan |

If the HAT button pin mapping conflicts with display SPI/GPIO on Radxa, button support may be implemented using alternative available GPIOs or by an enclosure-mounted button harness.

### 5.5 LCD HAT Pin Mapping Strategy

The Waveshare Zero LCD HAT (A) uses **two logical SPI buses** on the Raspberry Pi 40-pin header. The Radxa Zero 3W exposes **one primary header SPI bus (SPI3 M1)** on pins 19, 21, 23, 24, and 26. Pins 38 and 40 are GPIO/I2S functions on Radxa, not SPI.

#### 5.5.1 HAT Logical Signals (Raspberry Pi physical pin numbers)

| Signal | Physical Pin | HAT Use |
|---|---|---|
| MOSI0 | 38 | SPI bus A data |
| SCLK0 | 40 | SPI bus A clock |
| MOSI1 | 19 | SPI bus B data |
| SCLK1 | 23 | SPI bus B clock |
| CS0 | 12 | Display chip select |
| CS1 | 24 | Display chip select |
| CS2 | 26 | Display chip select |
| DC0 / DC1 / DC2 | 15 / 7 / 29 | Data/command per display |
| RST0 / RST1 / RST2 | 13 / 18 / 16 | Reset per display |
| BL0 / BL1 / BL2 | 35 / 33 / 32 | Backlight per display |
| KEY1 / KEY2 | 22 / 37 | Buttons |

#### 5.5.2 Radxa Integration Strategy (v1)

| Bus | Radxa Approach | Displays |
|---|---|---|
| Bus B (pins 19, 23, 24, 26) | Hardware SPI3 via `/dev/spidev3.0` with per-display GPIO for CS/DC/RST | Target: aux displays and/or main display — assign after bench test |
| Bus A (pins 38, 40) | **Software SPI (bit-bang)** on GPIO | Remaining display(s) not on hardware SPI3 |

Implementation rules:

1. Enable SPI3 overlay on vendor kernel (`rk3568-spi3-m1-cs0-spidev` via `rsetup` or `/boot/armbianEnv.txt`).
2. Map each display to a `DisplayDevice` config: `bus`, `cs_pin`, `dc_pin`, `rst_pin`, `bl_pin`, `width`, `height`, `driver`.
3. Serialize SPI transactions with a process-wide lock when multiple displays share one bus.
4. Never assume Raspberry Pi BCM numbering; use Radxa line numbers from `gpioinfo` during bring-up.
5. Document the final validated mapping in `config.json` after Milestone 1.

#### 5.5.3 Proposed Initial Display Assignment

Until bench validation completes, use this **proposed** assignment:

| Screen | Driver | Bus | Notes |
|---|---|---|---|
| Main (ST7789 240×240) | `st7789` | Hardware SPI3 if stable; else bit-bang bus A | Highest refresh priority |
| Aux left (ST7735S 160×80) | `st7735s` | Bit-bang bus A or shared SPI3 | Drive info |
| Aux right (ST7735S 160×80) | `st7735s` | Shared SPI3 | Security status |

Auxiliary screen roles are fixed in v1:

- **Aux left:** drive label, filesystem, capacity, USB speed.
- **Aux right:** engine, threat count, speed, CLEAN / SCANNING / THREAT status.

---

## 6. Operating System Design

### 6.1 Base OS

The appliance shall use the following **approved** Armbian image for Radxa Zero 3W:

| Field | Value |
|---|---|
| Distribution | Ubuntu 24.04 Noble |
| Variant | Minimal (CLI) |
| Kernel branch | **vendor** (Rockchip BSP 6.1.115) |
| Image size | ~343 MB |

**Not selected for v1:**

| Image | Reason |
|---|---|
| Ubuntu/Debian with `current` kernel (6.18.x) | Higher risk for SPI overlays and Radxa device-tree on Triple LCD HAT bring-up |
| Debian 13 Trixie | Newer base; less proven for this board/project combo |
| Ubuntu 26.04 Resolute | Too new for embedded appliance baseline |

**Rationale:** The vendor kernel provides better Radxa-specific hardware support (SPI3 overlays, GPIO, USB, Wi-Fi) than mainline/`current` builds. Ubuntu 24.04 LTS gives stable packages for Python, ClamAV, YARA, and systemd while matching the HLD’s headless server design.

First boot may be preconfigured using Armbian first-boot automation (`.not_logged_in_yet` on the boot partition) to set:

- Hostname.
- Admin user.
- SSH public key.
- Wi-Fi SSID/password (client mode).
- Timezone.
- Locale.

After first boot, enable SPI3 for display bring-up via `sudo rsetup` → Overlays → `rk3568-spi3-m1-cs0-spidev` (or Radxa vendor equivalent), then reboot.

### 6.2 Required Packages

| Category | Packages / Tools |
|---|---|
| Python runtime | Python 3.11+, `venv`, `pip` |
| API | FastAPI, Uvicorn, Pydantic |
| Malware scanning | ClamAV, `clamd`, `clamdscan`, `clamscan`, YARA, Python YARA bindings |
| Filesystems | `exfatprogs`, `ntfs-3g`, ext filesystem tools |
| Device handling | `udev`, `systemd`, `lsblk`, `blkid`, `mount`, `umount` |
| Data storage | SQLite |
| Reports | Jinja2 or equivalent HTML templating |
| Display prototype | `spidev`, GPIO library compatible with Radxa Linux |

### 6.3 systemd Units

| Unit | Responsibility |
|---|---|
| `portable-av-engine.service` | Runs scan engine and FastAPI application |
| `portable-av-display.service` | Runs userspace display manager and button handler |
| `portable-av-mount@.service` | Handles media mount/unmount work triggered by `udev` |
| `clamav-daemon.service` | Keeps ClamAV daemon running when memory allows |
| `clamav-freshclam.service` / timer | Updates ClamAV signatures over Wi-Fi |

### 6.4 Boot and Startup Sequence

```
Power on
    |
    v
Armbian kernel + systemd
    |
    +--> clamav-daemon.service (if enabled)
    |
    +--> portable-av-engine.service
    |         |
    |         +--> Load config.json
    |         +--> Open SQLite history.db
    |         +--> Start FastAPI on 127.0.0.1:8080 (LAN bind optional)
    |         +--> Enter IDLE state
    |
    +--> portable-av-display.service
              |
              +--> Init LcdHatDriver (SPI + GPIO)
              +--> Connect WebSocket to engine
              +--> Render idle screen
```

Startup guarantees:

- Scan engine MUST reach `IDLE` even if display service fails.
- Display service MUST restart independently and resubscribe to WebSocket.
- No scan starts automatically on boot.

### 6.5 First-Time Provisioning

Provisioning uses Armbian `.not_logged_in_yet` on the boot partition before first power-on:

| Setting | Purpose |
|---|---|
| `PRESET_USER_NAME` / `PRESET_USER_PASSWORD` | Admin account |
| `PRESET_USER_KEY` | SSH public key |
| `PRESET_NET_WIFI_ENABLED` | Enable Wi-Fi client |
| `PRESET_NET_WIFI_SSID` / `PRESET_NET_WIFI_KEY` | Wi-Fi credentials |
| `PRESET_NET_USE_STATIC=0` | Enable DHCP |

Post-install steps (automated via `/root/provisioning.sh` or manual):

1. Install Ubuntu packages and Python venv.
2. Create `portable-av` system user.
3. Deploy application to `/opt/portable-av/`.
4. Install systemd units.
5. Install `udev` rules and ClamAV/YARA configs.
6. Generate API token and store hash in config.
7. Reboot and run Milestone 1 acceptance tests.

---

## 7. Software Architecture

### 7.1 Process Architecture

```
+-----------------------------+
| portable-av-display.service |
| - SPI LCD rendering         |
| - button input              |
| - subscribes to WebSocket   |
+--------------+--------------+
               |
               | REST / WebSocket localhost
               v
+-----------------------------+
| portable-av-engine.service  |
| - FastAPI                   |
| - scan controller           |
| - event broker              |
| - history/report manager    |
+--------------+--------------+
               |
      +--------+--------+
      |                 |
      v                 v
+------------+   +------------------+
| clamd /    |   | udev/systemd     |
| clamdscan  |   | mount manager    |
+------------+   +------------------+
      |
      v
+------------+
| YARA scan  |
+------------+
```

### 7.2 Module Layout

Proposed source tree:

```
portable_av/
  api/
    app.py
    auth.py
    routes_scan.py
    routes_history.py
    routes_config.py
    websocket.py
  engine/
    scan_controller.py
    scan_models.py
    file_enumerator.py
    hashing.py
    clamav_adapter.py
    yara_adapter.py
    event_bus.py
  mount/
    device_detector.py
    mount_manager.py
    filesystem_info.py
  reports/
    report_writer.py
    templates/
  history/
    db.py
    repository.py
  display/
    display_manager.py
    lcd_hat_driver.py
    screens.py
    buttons.py
  update/
    freshclam_runner.py
    yara_rules.py
  common/
    config.py
    logging.py
    errors.py
```

### 7.3 Component Interfaces

| From | To | Interface |
|---|---|---|
| Display Manager | Scan Engine | WebSocket `ws://127.0.0.1:8080/api/v1/scan/events` |
| Display Manager | Scan Engine | REST for menu actions (`POST /api/v1/scan`, etc.) |
| Web UI | Scan Engine | REST + WebSocket on LAN |
| udev | Mount helper | `systemd-run` or `portable-av-mount@.service` with device path |
| Mount helper | Scan Engine | Unix domain socket or HTTP callback to `/api/v1/internal/drive` |
| Scan Controller | ClamAV | `clamdscan` subprocess or socket to `clamd` |
| Scan Controller | YARA | `yara-python` compiled ruleset |
| Scan Controller | SQLite | `history.repository` |
| freshclam runner | ClamAV | `freshclam` CLI |

Internal-only endpoints (localhost bind) SHOULD be used for mount callbacks to avoid exposing device control on the LAN.

### 7.4 Engine State Machine

```
BOOT --> IDLE --> MOUNTED --> MENU --> SCANNING --> COMPLETE --> MENU
                  |    ^         |         |            |
                  |    |         |         +--> THREAT_PROMPT
                  |    |         |         |
                  +----+---------+---------+--> ERROR --> IDLE
```

| State | Entry Condition | Exit Actions |
|---|---|---|
| `IDLE` | Boot complete or media removed | Show "Insert drive" |
| `MOUNTED` | Read-only mount success | Show drive summary on aux left |
| `MENU` | Enter pressed with media present | Offer Quick / Full Scan |
| `SCANNING` | Scan started | Emit progress events |
| `THREAT_PROMPT` | Detection event | Wait for continue/stop/details |
| `COMPLETE` | Scan finished or cancelled | Write reports, update history |
| `ERROR` | Mount failure, OOM, media removed mid-scan | Log error, show message |

Only one scan MAY be active. Starting a scan while another is running returns HTTP 409.

---

## 8. Data Flow

### 8.1 Scan Start Flow

1. Media is inserted.
2. `udev` identifies a block device.
3. `portable-av-mount@.service` starts for the device.
4. Mount manager verifies filesystem type.
5. Mount manager mounts the volume read-only under `/mnt/portable-av/<device-id>`.
6. Engine updates `drive` state and emits `drive_mounted` event.
7. Display manager receives event and updates local display.
8. Operator selects Quick Scan or Full Scan.
9. API or button event calls `scan_controller.start(mode)`.
10. Scan controller creates a scan row in SQLite with status `RUNNING`.
11. Scan pipeline enumerates files and starts scanning.

### 8.2 Scan Pipeline Flow

```
Read-only mount
      |
      v
File enumeration
      |
      v
For each file:
  - classify path/type
  - apply Quick/Full filter
  - compute SHA-256
  - submit to ClamAV
  - submit to YARA when enabled for mode/type
  - record result
  - emit progress event
      |
      v
Finalize scan
      |
      v
Write SQLite summary + TXT/HTML reports
```

### 8.3 Threat Event Flow

1. ClamAV or YARA returns a detection.
2. Scan controller records detection in memory and SQLite.
3. Event bus emits `threat_detected`.
4. Display manager shows warning state.
5. WebSocket clients receive alert.
6. Operator may continue, view details, or stop scan.
7. Since media is read-only, no quarantine/delete action is offered.

---

## 9. Scan Design

### 9.1 Scan Modes

| Mode | v1 Behavior |
|---|---|
| Quick Scan | Scan executables, Office documents, scripts, and archives. |
| Full Scan | Scan all regular files. |
| Deep Scan | Not available in v1; deferred to v2. |

### 9.2 ClamAV Strategy

Target design:

- Use `clamd` and `clamdscan` for normal operation.
- Keep ClamAV definitions loaded to avoid repeated startup overhead.
- Benchmark memory usage on the 1 GB Radxa target.
- If `clamd` causes memory pressure, fall back to `clamscan` for v1.

ClamAV archive handling:

- Use ClamAV's built-in archive scanning only.
- Configure conservative limits for file size, recursion, scan time, and temporary storage.
- Do not implement custom archive extraction in v1.

### 9.3 YARA Strategy

YARA is enabled in v1.

Rules:

- YARA runs after or alongside ClamAV depending on benchmark results.
- Initial implementation may run YARA only on Quick Scan file types and all Full Scan files that are below a configured size limit.
- YARA rules are manually installed via SSH or Web UI upload/copy.
- Automatic remote YARA feed sync is deferred.

### 9.4 Concurrency Strategy

The HLD treats concurrency as benchmark-dependent. The safe default is a single active scan pipeline:

- One file processed at a time.
- Progress event emitted after each file or time slice.
- Optional future setting: `max_workers = 2` if memory and CPU benchmarks allow it.

This protects the 1 GB RAM target from ClamAV/YARA contention and excessive temporary file usage.

### 9.5 Quick Scan File Selection

Quick Scan includes files matching any of the following (case-insensitive extension match):

| Category | Extensions |
|---|---|
| Executables | `exe`, `dll`, `sys`, `scr`, `com`, `msi`, `cab`, `elf`, `so`, `bin`, `apk`, `dmg`, `pkg` |
| Scripts | `ps1`, `vbs`, `js`, `jse`, `wsf`, `bat`, `cmd`, `sh`, `py`, `pl`, `rb` |
| Office | `doc`, `docx`, `docm`, `xls`, `xlsx`, `xlsm`, `ppt`, `pptx`, `pptm`, `odt`, `ods`, `odp`, `rtf` |
| Archives | `zip`, `7z`, `rar`, `tar`, `gz`, `bz2`, `xz`, `iso` |

Files without matching extensions are skipped in Quick Scan. Full Scan includes all regular files subject to size and timeout limits.

### 9.6 ClamAV and YARA Configuration (v1 Defaults)

These values are starting points; tune during Milestone 3 benchmarks.

**`clamd.conf` (key limits):**

| Directive | Value | Rationale |
|---|---|---|
| `MaxFileSize` | 100M | Protect 1 GB RAM / SD wear |
| `MaxScanSize` | 200M | Cap archive expansion |
| `MaxRecursion` | 5 | Built-in archive depth only |
| `MaxFiles` | 10000 | Per-archive file cap |
| `MaxEmbeddedPE` | 10M | PE extraction limit |
| `StreamMaxLength` | 25M | Streaming cap |
| `TemporaryDirectory` | `/tmp/portable-av/clamav` | On microSD tmpfs or disk |
| `LeaveTemporaryFiles` | no | Cleanup after scan |

**Scan engine limits:**

| Setting | Default |
|---|---|
| `max_file_size_bytes` | 104857600 (100 MB) |
| `per_file_timeout_sec` | 120 |
| `yara_max_file_size_bytes` | 52428800 (50 MB) |
| `hash_max_file_size_bytes` | 104857600 (100 MB) |
| `clamav_mode` | `clamd` (fallback `clamscan`) |

**YARA:**

- Rules directory: `/var/lib/portable-av/yara/rules/`
- Compile all `*.yar` / `*.yara` at startup or on rule update.
- If compilation fails, keep last known-good compiled ruleset.

---

## 10. Mount Manager Design

### 10.1 Responsibilities

The mount manager is responsible for:

- Detecting inserted removable media.
- Identifying filesystem type and volume metadata.
- Mounting supported filesystems read-only.
- Rejecting unsupported filesystems.
- Unmounting safely when scan is complete or device is removed.
- Reporting mount state to the engine.

### 10.2 Mount Policy

All removable media must be mounted read-only.

Example mount flags:

```
ro,nosuid,nodev,noexec
```

Filesystem-specific notes:

| Filesystem | v1 Support |
|---|---|
| FAT32 | Yes |
| exFAT | Yes |
| NTFS | Yes, via `ntfs-3g` read-only |
| ext2/3/4 | Yes, read-only |
| APFS/HFS+/Btrfs/XFS | No v1 requirement |

### 10.3 Unsupported Device Policy

Unsupported or high-power device categories:

- USB HDDs are out of scope.
- Network shares are out of scope.
- Phones in MTP/PTP mode are out of scope.
- iPhone scanning is out of scope.

If a USB HDD is detected, the system should show an unsupported media message rather than attempting a scan.

### 10.4 udev and systemd Integration

**udev rule** (conceptual):

```
ACTION=="add", SUBSYSTEM=="block", ENV{ID_BUS}=="usb", TAG+="systemd", ENV{SYSTEMD_WANTS}="portable-av-mount@%k.service"
```

**`portable-av-mount@.service`** responsibilities:

1. Wait for partition node to settle (`/dev/%i` or child partition).
2. Call `mount_manager mount /dev/<partition>`.
3. Write mount metadata to `/run/portable-av/drive.json`.
4. Notify engine via internal callback.

**Removal:**

```
ACTION=="remove", SUBSYSTEM=="block", RUN+="/usr/local/bin/portable-av-unmount %k"
```

On removal during scan, engine transitions to `ERROR` / `INTERRUPTED` and unmounts cleanly.

**Mount path convention:**

```
/mnt/portable-av/<volume-uuid>/
```

---

## 11. API Design

### 11.1 API Technology

The API uses FastAPI with Uvicorn.

Reasons:

- Native REST and WebSocket support.
- OpenAPI documentation generated automatically.
- Strong request/response validation with Pydantic.
- Good fit for future Android app integration.

### 11.2 Authentication

v1 uses local-network token/password authentication:

- Read-only status endpoints may be unauthenticated or token-protected based on config.
- Scan control, config changes, history deletion, and update actions require authentication.
- Token stored hashed on the appliance.
- API should bind to LAN interface only when Wi-Fi is configured.

### 11.3 Endpoint Summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/status` | System and engine status |
| GET | `/api/v1/drive` | Mounted drive metadata |
| POST | `/api/v1/scan` | Start Quick or Full Scan |
| DELETE | `/api/v1/scan` | Cancel active scan |
| GET | `/api/v1/scan/progress` | Current progress snapshot |
| WS | `/api/v1/scan/events` | Live events |
| GET | `/api/v1/history` | Scan history list |
| GET | `/api/v1/history/{scan_id}` | Scan detail |
| GET | `/api/v1/history/{scan_id}/report.txt` | TXT report |
| GET | `/api/v1/history/{scan_id}/report.html` | HTML report |
| POST | `/api/v1/update/clamav` | Run `freshclam` |
| POST | `/api/v1/update/yara` | Upload/copy YARA rules manually |
| GET | `/api/v1/config` | Read configuration |
| PUT | `/api/v1/config` | Update configuration |

### 11.4 WebSocket Events

Event names:

- `system_status`
- `drive_mounted`
- `drive_removed`
- `scan_started`
- `scan_progress`
- `stage_changed`
- `threat_detected`
- `scan_cancelled`
- `scan_completed`
- `scan_error`

Example event:

```json
{
  "type": "scan_progress",
  "scan_id": "20260709-001",
  "mode": "quick",
  "stage": "clamav",
  "current_file": "/Documents/report.xlsm",
  "files_scanned": 18423,
  "files_total": 34125,
  "progress_percent": 54.0,
  "threats": 0,
  "speed_mbps": 72.0
}
```

---

## 12. Display Manager Design

### 12.1 Prototype Strategy

The first prototype focuses on proving:

- SPI communication with the ST7789 main display.
- SPI communication with both ST7735S auxiliary displays.
- Backlight control if exposed.
- Button input handling.
- Basic display refresh while the scan engine runs independently.

### 12.2 Userspace Driver

The userspace driver should provide a small abstraction:

```text
LcdHatDriver
  init()
  clear(screen_id)
  draw_image(screen_id, image_buffer)
  set_backlight(screen_id, enabled)
  close()
```

Rendering strategy:

- Use Pillow or LVGL-backed buffers to render screen images.
- Push full or partial frame updates over SPI.
- Start with low refresh rate: 1-2 Hz during scan.
- Increase only if stable.

### 12.3 Display UI Scope

The exact UI layout is TBD. The HLD preserves the SRS display intent:

- Main display: task/progress/alert.
- Aux display 1: compact drive or media status.
- Aux display 2: compact security or scan status.

Because the main screen is 240x240 and the aux screens are 160x80, the previous large-screen UI concept shall not be used directly.

### 12.4 v1 UI Layout Specification

The v1 UI adapts the SRS Threat Meter concept to the 240×240 main display.

#### Main Display (240×240) — Scanning State

```
+--------------------------------+
| SCANNING          [|||||....] |  <- 12-segment horizontal meter
| Quick Scan                     |
|                                |
| report.xlsm                    |  <- filename only, truncated
|                                |
| 18423/34125        ETA 03:17   |
+--------------------------------+
```

| Element | Specification |
|---|---|
| Threat Meter | 12 horizontal segments, top-right; fill left-to-right |
| Segment mapping | `filled = floor(progress_percent / 8.33)` |
| Colors | Green=ClamAV, Blue=hashing, Purple=YARA, Orange=suspicious, Red=threat |
| On threat | All filled segments turn red immediately |
| Filename | Basename only; max ~18 chars with ellipsis |
| Progress text | `files_scanned/files_total` and `ETA mm:ss` |

#### Main Display — Other States

| State | Content |
|---|---|
| Idle | `Insert drive` centered |
| Mounted | `Drive ready` + `Press Enter` |
| Menu | `> Quick Scan` / `  Full Scan` |
| Threat prompt | `THREAT FOUND` + basename + `Continue?` |
| Complete | `CLEAN` or `THREATS: N` large text |
| Error | Short error + `Press Enter` |

#### Aux Left (160×80) — Drive Info

```
Samsung
NTFS 32GB
USB 3.0
```

#### Aux Right (160×80) — Security

```
ClamAV+YARA
Threats: 0
72 MB/s
 CLEAN
```

Status line uses large text: `CLEAN`, `SCAN`, or `THREAT`.

#### Refresh Rate

| Mode | Target |
|---|---|
| Idle | 0.5 Hz |
| Scanning | 2 Hz |
| Threat alert | Immediate full redraw |

### 12.5 Local Menu Model

Display manager implements a small state machine mirroring engine states. Button actions call the REST API:

| Button | API Call |
|---|---|
| Enter on menu | `POST /api/v1/scan` with selected mode |
| Double-click Enter | `DELETE /api/v1/scan` |
| Long-press Enter | Local menu back (no API) |

---

## 13. Persistence Design

### 13.1 Storage Locations

| Data | Location |
|---|---|
| Configuration | `/etc/portable-av/config.json` |
| Runtime state | `/run/portable-av/` |
| Scan history DB | `/var/lib/portable-av/history.db` |
| Reports | `/var/lib/portable-av/reports/<scan_id>/` |
| YARA rules | `/var/lib/portable-av/yara/rules/` |
| Temporary scanner files | `/tmp/portable-av/` or configured temp dir |
| Logs | `/var/log/portable-av/` |

### 13.2 SQLite Schema Summary

Tables:

- `scans`
- `detections`
- `files_sampled` (optional; limited metadata, not every clean file unless configured)
- `events`
- `signature_updates`

`scans` key fields:

- `scan_id`
- `started_at`
- `ended_at`
- `status`
- `mode`
- `device_label`
- `device_uuid`
- `filesystem`
- `files_total`
- `files_scanned`
- `bytes_scanned`
- `threat_count`
- `report_txt_path`
- `report_html_path`

`detections` key fields:

- `id`
- `scan_id`
- `engine`
- `signature`
- `file_path`
- `sha256`
- `detected_at`
- `action`

### 13.3 32 GB microSD Constraints

The system should manage storage conservatively:

- OS + core packages target: <= 4 GB.
- Signatures and YARA rules: monitored.
- Reports retained until storage threshold is reached.
- Warn at 90% usage.
- Block new scans at 95% usage.

### 13.4 Configuration Schema

File: `/etc/portable-av/config.json`

```json
{
  "version": 1,
  "api": {
    "bind_host": "0.0.0.0",
    "bind_port": 8080,
    "auth_token_hash": "<bcrypt>",
    "allow_unauthenticated_read": false
  },
  "scan": {
    "default_mode": "quick",
    "clamav_mode": "clamd",
    "max_file_size_bytes": 104857600,
    "per_file_timeout_sec": 120,
    "yara_enabled": true,
    "yara_max_file_size_bytes": 52428800
  },
  "display": {
    "refresh_hz_idle": 0.5,
    "refresh_hz_scanning": 2,
    "devices": []
  },
  "storage": {
    "warn_percent": 90,
    "block_percent": 95
  },
  "updates": {
    "freshclam_schedule": "03:00"
  }
}
```

Display `devices[]` entries are populated after Milestone 1 pin validation.

---

## 14. Updates Design

### 14.1 ClamAV Updates

ClamAV signatures are updated with `freshclam` over Wi-Fi.

Update flow:

1. User starts update via Web UI/API or scheduled timer.
2. Engine checks that no scan is active.
3. `freshclam` runs.
4. Result is recorded in SQLite.
5. Display/API reports success or failure.

### 14.2 YARA Updates

YARA rules are manually managed in v1.

Supported paths:

- Copy rules over SSH.
- Upload rules through Web UI/API if implemented in v1.

The engine validates:

- Rule syntax.
- File extension.
- Maximum total rule directory size.

Remote YARA feed sync is deferred.

---

## 15. Security Design

### 15.1 Media Isolation

All external media are mounted:

- Read-only.
- `nosuid`.
- `nodev`.
- `noexec`.

The scan engine never executes files from scanned media.

### 15.2 Service Privileges

Design target:

- `portable-av-engine` runs as unprivileged user `portable-av`.
- Mount operations are isolated to a small privileged helper or systemd/udev workflow.
- Display manager may need GPIO/SPI group permissions but should not run as root long-term if avoidable.

### 15.3 Network Security

- SSH uses key-based authentication.
- Web/API write operations require token/password auth.
- No cloud upload is performed automatically.
- Wi-Fi client mode only in v1.

---

## 16. Error Handling Design

| Error | Handling |
|---|---|
| Unsupported filesystem | Show unsupported media state; do not mount read-write. |
| USB HDD detected | Show unsupported media state; do not scan. |
| Media removed during scan | Abort scan, mark `INTERRUPTED`, generate partial report if possible. |
| ClamAV daemon unavailable | Attempt restart; fall back to `clamscan` if configured. |
| YARA rule compile error | Reject rule set and keep previous valid set. |
| Display manager crash | Restart via systemd; scan engine continues headless. |
| API crash | Restart via systemd; active scan state recovered if possible. |
| Storage above 90% | Warn user/admin. |
| Storage above 95% | Block new scans. |
| Wi-Fi unavailable | Scans still work; updates and Web UI may be unavailable. |

---

## 17. Prototype Milestones

### Milestone 1: Hardware Bring-Up

Goal: prove the fixed hardware stack.

Acceptance:

- Radxa Zero 3W boots headless Armbian Ubuntu 24.04 Noble (vendor kernel) from 32 GB microSD.
- SSH login works over Wi-Fi.
- SPI is accessible from userspace.
- Main ST7789 display shows a test image.
- Both ST7735S displays show test images.
- Buttons produce events.
- System is stable for 30 minutes with displays active.

### Milestone 2: Display Service Skeleton

Goal: prove local UI process.

Acceptance:

- `portable-av-display.service` starts at boot.
- Displays show idle/status screen.
- Button events are debounced.
- Display service reconnects to engine API/WebSocket after restart.

### Milestone 3: Headless Scan Prototype

Goal: prove read-only scanning.

Acceptance:

- USB flash drive mounts read-only.
- Quick Scan runs through API or CLI.
- EICAR detection is reported.
- TXT and HTML reports are written.

### Milestone 4: Integrated Appliance Loop

Goal: prove end-to-end appliance behavior.

Acceptance:

- Insert drive.
- Select scan from buttons.
- Progress appears on displays.
- Threat detection changes display state.
- Report appears in Web UI.

---

## 18. Web UI Design (v1 Scope)

The Web UI is a static single-page app served by FastAPI from `/static/`.

| Page | Purpose |
|---|---|
| Dashboard | Current drive, scan status, live progress |
| Scan | Start Quick/Full Scan, cancel scan |
| History | Browse past scans, download reports |
| Settings | Wi-Fi status (read-only in v1), API token rotate, update triggers |
| Updates | Run `freshclam`, upload YARA rules |

v1 Web UI does NOT include:

- Wi-Fi AP onboarding UI.
- Deep Scan controls.
- Remote quarantine/delete.

Authentication: Bearer token in `Authorization` header for write operations.

---

## 19. Deployment Design

### 19.1 Installation Layout

| Path | Content |
|---|---|
| `/opt/portable-av/venv/` | Python virtual environment |
| `/opt/portable-av/app/` | Application source |
| `/etc/portable-av/` | Configuration |
| `/var/lib/portable-av/` | Data, reports, YARA rules |
| `/var/log/portable-av/` | Logs |
| `/etc/systemd/system/portable-av-*.service` | systemd units |
| `/etc/udev/rules.d/99-portable-av.rules` | udev rules |

### 19.2 Install Flow

1. Flash **Armbian Ubuntu 24.04 Noble Minimal (CLI), vendor kernel** to 32 GB microSD.
2. Apply first-boot Wi-Fi and SSH provisioning.
3. Run `install.sh` from deployment package (creates user, dirs, venv, units).
4. Reboot.
5. Execute milestone acceptance checklist.

### 19.3 Logging

| Log | Rotation |
|---|---|
| `/var/log/portable-av/engine.log` | 10 MB × 5 files |
| `/var/log/portable-av/display.log` | 5 MB × 3 files |
| journald for systemd units | Default |

Structured JSON log lines: `timestamp`, `level`, `component`, `message`, `scan_id`.

---

## 20. Risks and Mitigations

| ID | Risk | Mitigation |
|---|---|---|
| HLD-RISK-001 | Triple LCD HAT may not map cleanly to Radxa SPI/GPIO. | Prototype userspace SPI first; document pin mapping; move to custom overlay only if needed. |
| HLD-RISK-002 | Display HAT 3.3V load may destabilize board. | Bench-test voltage; add external regulator if instability appears. |
| HLD-RISK-003 | 1 GB RAM may be tight for `clamd` + YARA. | Benchmark `clamd` vs `clamscan`; use single-file pipeline; enforce file and archive limits. |
| HLD-RISK-004 | 32 GB microSD wear from reports/logs/temp files. | Log rotation, limited temp files, storage thresholds, avoid storing clean-file metadata by default. |
| HLD-RISK-005 | ClamAV archive scanning may consume excessive resources on crafted archives. | Configure ClamAV limits; no custom recursive extraction in v1. |
| HLD-RISK-006 | Web/API auth on LAN may be misconfigured. | Token auth for control endpoints; SSH key auth; no unauthenticated write operations. |

---

## 21. Validation Checklist (Prototype)

Items below move from "open" to "closed" only after bench test on real hardware.

| ID | Validation | Pass Criteria |
|---|---|---|
| VAL-001 | SPI3 hardware bus | Main or aux display stable at 2 Hz for 30 min |
| VAL-002 | Bit-bang bus A | Remaining display(s) render without corruption |
| VAL-003 | 3.3V rail | No brownout or reboot with all displays on |
| VAL-004 | `clamd` memory | RSS + scan peak < 800 MB during Full Scan sample |
| VAL-005 | ClamAV archive limits | Zip bomb test does not OOM or fill SD |
| VAL-006 | USB HDD reject | Rotational HDD shows unsupported message |

---

## 22. Open Items

| ID | Item | Status |
|---|---|---|
| OPEN-001 | Final validated pin map in `config.json` | Pending VAL-001/002 |
| OPEN-002 | `clamd` vs `clamscan` final choice | Pending VAL-004 |
| OPEN-003 | External 3.3V regulator needed? | Pending VAL-003 |
| OPEN-004 | Threat Meter segment count (12 vs 16) | Tune during UI bring-up |

All other HLD sections are **design-complete** for v1 implementation.

---

## 23. Traceability

| HLD Area | SRS Requirements |
|---|---|
| Hardware | FR-001 to FR-007, NFR-050, NFR-051 |
| Mount Manager | FR-001 to FR-007, SEC-001 |
| Scan Pipeline | FR-010 to FR-026 |
| Display Manager | FR-030 to FR-037, UI TBD constraints |
| Threat Handling | FR-040 to FR-045 |
| Reports/History | FR-050 to FR-056 |
| Updates | FR-060 to FR-065 |
| API/Web UI | FR-070 to FR-075 |
| Buttons | FR-080 to FR-083 |
| Archive Policy | FR-022, FR-090 to FR-092 |

---

## Appendix A: SQLite DDL (v1)

```sql
CREATE TABLE scans (
    scan_id         TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    status          TEXT NOT NULL,
    mode            TEXT NOT NULL,
    device_label    TEXT,
    device_uuid     TEXT,
    filesystem      TEXT,
    mount_path      TEXT,
    files_total     INTEGER DEFAULT 0,
    files_scanned   INTEGER DEFAULT 0,
    bytes_scanned   INTEGER DEFAULT 0,
    threat_count    INTEGER DEFAULT 0,
    report_txt_path TEXT,
    report_html_path TEXT
);

CREATE TABLE detections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id         TEXT NOT NULL REFERENCES scans(scan_id),
    engine          TEXT NOT NULL,
    signature       TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    sha256          TEXT,
    detected_at     TEXT NOT NULL,
    action          TEXT
);

CREATE TABLE signature_updates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engine          TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    success         INTEGER NOT NULL,
    message         TEXT
);

CREATE INDEX idx_detections_scan_id ON detections(scan_id);
CREATE INDEX idx_scans_started_at ON scans(started_at);
```

---

## Appendix B: systemd Unit Sketch

**`portable-av-engine.service`:**

```ini
[Unit]
Description=Portable AV Scan Engine
After=network.target clamav-daemon.service
Wants=clamav-daemon.service

[Service]
Type=simple
User=portable-av
Group=portable-av
WorkingDirectory=/opt/portable-av/app
ExecStart=/opt/portable-av/venv/bin/uvicorn portable_av.api.app:app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`portable-av-display.service`:**

```ini
[Unit]
Description=Portable AV Display Manager
After=portable-av-engine.service
Requires=portable-av-engine.service

[Service]
Type=simple
User=portable-av
Group=portable-av
SupplementaryGroups=gpio spi
WorkingDirectory=/opt/portable-av/app
ExecStart=/opt/portable-av/venv/bin/python -m portable_av.display.display_manager
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## Appendix C: Document History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-07-09 | Initial HLD draft from confirmed SRS and HLD decision session |
| 1.0 | 2026-07-09 | Completed HLD: pin mapping strategy, UI layout, config, ClamAV limits, udev/systemd, deployment, validation checklist |
| 1.1 | 2026-07-09 | OS baseline: Armbian Ubuntu 24.04 Noble Minimal, vendor kernel 6.1.115 |

---

*End of Document*
