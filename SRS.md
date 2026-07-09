# Software Requirements Specification (SRS)

## Portable Antivirus Appliance

| Field | Value |
|---|---|
| **Document ID** | SRS-PAV-001 |
| **Version** | 1.1 |
| **Date** | 2026-07-09 |
| **Status** | Draft — Approved Requirements Baseline |
| **Target Platform** | Radxa Zero 3W, Armbian Ubuntu 24.04 Noble Minimal (vendor kernel) |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [User Interface Specification](#5-user-interface-specification)
6. [Hardware Requirements](#6-hardware-requirements)
7. [Software Architecture](#7-software-architecture)
8. [State Machine](#8-state-machine)
9. [Security Requirements](#9-security-requirements)
10. [Error Handling](#10-error-handling)
11. [Acceptance Criteria](#11-acceptance-criteria)
12. [Future Enhancements](#12-future-enhancements)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification defines the functional and non-functional requirements for a **portable malware scanning appliance** — a dedicated embedded device that scans removable storage media for malware without requiring a host PC.

The document serves as the authoritative requirements baseline for subsequent High-Level Design (HLD), software architecture, UI specification, implementation plan, and acceptance testing.

### 1.2 Scope

The appliance shall:

- Accept removable storage devices (USB flash drives, portable SSDs, SD/microSD cards, and archive files).
- Mount all external media **read-only**.
- Scan files using **ClamAV** and **YARA** signature engines (v1).
- Present scan progress and results on **three independent color displays**.
- Expose a **headless scan engine** via REST API and WebSocket for embedded UI, web UI, and future Android client.
- Retain unlimited scan history (bounded only by internal storage).
- Generate scan reports in **TXT** and **HTML** formats.
- Update malware signatures over **Wi-Fi**.

The appliance shall **not** (v1):

- Modify, quarantine, or delete files on scanned media (read-only policy).
- Support USB HDDs or powered HDD workflows.
- Support iPhone, Android MTP, or network share scanning.
- Include heuristic, reputation, or specialized analyzers beyond ClamAV and YARA (deferred to v2).
- Support Deep Scan or custom recursive archive extraction (deferred to v2 due to 1 GB RAM target).

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| **Appliance** | The complete portable scanner hardware + firmware + software |
| **Aux Display** | One of the two 0.96-inch auxiliary displays on the Triple IPS LCD HAT |
| **Main Display** | The 1.3-inch center display on the Triple IPS LCD HAT |
| **Threat Meter** | Segmented progress/status indicator concept; exact v1 layout is TBD |
| **Scan Engine** | Headless background service performing mount, enumeration, and analysis |
| **Stage** | Current analysis phase (e.g., hashing, ClamAV, YARA) |
| **YARA** | Pattern-matching tool for malware research and detection |
| **ClamAV** | Open-source antivirus engine |
| **SRS** | Software Requirements Specification |
| **FR** | Functional Requirement |
| **NFR** | Non-Functional Requirement |

### 1.4 References

| ID | Document |
|---|---|
| REF-001 | IEEE Std 830-1998 (SRS recommended practice) |
| REF-002 | ClamAV documentation — https://docs.clamav.net |
| REF-003 | YARA documentation — https://yara.readthedocs.io |
| REF-004 | Radxa Zero 3W hardware documentation |
| REF-005 | Armbian documentation — https://docs.armbian.com |
| REF-006 | Armbian Ubuntu 24.04 Noble image for Radxa Zero 3W (vendor kernel 6.1.115) |

### 1.5 Overview

Section 2 describes the product context. Sections 3–4 enumerate functional and non-functional requirements. Section 5 specifies the three-display UI including the segmented Threat Meter. Sections 6–7 cover hardware and software architecture. Sections 8–10 define behavior under state transitions, security constraints, and fault conditions. Section 11 lists acceptance tests. Section 12 captures the v2+ roadmap.

---

## 2. Overall Description

### 2.1 Product Perspective

The portable antivirus appliance is a **standalone embedded system** resembling commercial laboratory or industrial inspection equipment. It operates independently of a host computer while optionally exposing network services (SSH, Web UI, REST API, WebSocket) for administration, remote monitoring, and companion applications.

```
┌─────────────────────────────────────────────────────────────┐
│                    Portable Antivirus Appliance              │
│  ┌──────────────┐  ┌─────────────────────┐  ┌──────────────┐ │
│  │ Left Aux     │  │ Main Display        │  │ Right Aux    │ │
│  │ Drive Info   │  │ Task + Threat Meter │  │ Security     │ │
│  └──────────────┘  └─────────────────────┘  └──────────────┘ │
│  ┌─────────┐ ┌─────────┐                                     │
│  │ Btn 1   │ │ Btn 2   │   [Radxa Zero 3W + Triple LCD HAT] │
│  │ Down    │ │ Enter   │                                     │
│  └─────────┘ └─────────┘                                     │
└─────────────────────────────────────────────────────────────┘
         │ USB Host Port(s)          │ Wi-Fi
         ▼                             ▼
   Removable Media              Admin / Web / Android
```

### 2.2 Product Functions

| Function | Description |
|---|---|
| Device detection | Auto-detect USB mass storage and SD card insertion |
| Read-only mount | Mount all external filesystems read-only |
| File enumeration | Walk directory tree respecting scan mode filters |
| Malware scanning | ClamAV signature scan + YARA rule matching |
| Progress reporting | Real-time updates to displays and WebSocket clients |
| Threat alerting | Visual and API notification on detection |
| Report generation | TXT and HTML reports saved to internal storage |
| History management | Persistent log of all past scans |
| Signature update | Download and apply ClamAV/YARA updates over Wi-Fi |
| Configuration | Scan mode selection, Wi-Fi setup, settings via UI and Web |

### 2.3 User Classes and Characteristics

| User Class | Description | Primary Interface |
|---|---|---|
| **Operator** | Inserts drive, starts scan, reads result at a glance | Physical displays + buttons |
| **Administrator** | Configures Wi-Fi, updates signatures, reviews history | Web UI or SSH |
| **Integrator** | Builds companion apps or automation | REST API + WebSocket |
| **Forensic examiner** | Uses read-only scanning to inspect media without altering evidence | Physical displays + HTML reports |

### 2.4 Operating Environment

| Component | Specification |
|---|---|
| Board | Radxa Zero 3W |
| OS | Armbian **Ubuntu 24.04 Noble** Minimal (CLI), **vendor** kernel **6.1.115** |
| OS image | ~343 MB Armbian build; not Debian 13, not Ubuntu 26.04, not `current` (6.18.x) kernel |
| Kernel choice | Vendor kernel preferred for SPI/GPIO overlays, USB, and Radxa device-tree support |
| Runtime | Python 3.11+ |
| Scan engines | ClamAV 1.x, YARA 4.x |
| Embedded UI | LVGL (Python bindings or native) |
| Internal storage | 32 GB microSD card only for OS, databases, reports, and history |
| Network | Onboard Wi-Fi (802.11 b/g/n/ac) |
| Displays | Waveshare Zero LCD HAT (A) / Triple IPS LCD HAT |
| Input | 2× physical buttons |

### 2.5 Design and Implementation Constraints

1. **Read-only mounts** — All external media MUST be mounted with the `ro` flag. No exceptions in v1.
2. **Headless operation** — Scanning MUST proceed when no display client, web browser, or API consumer is connected.
3. **Display hardware fixed** — The appliance uses the Waveshare Zero LCD HAT (A): one 1.3-inch ST7789 LCD (240×240) and two 0.96-inch ST7735S LCDs (160×80), all over SPI.
4. **API-first** — All UI surfaces (embedded LVGL, Web UI, future Android app) consume the same scan engine API.
5. **No hardware feedback beyond displays** — No RGB LED, buzzer, or vibration motor in v1.

### 2.6 Assumptions and Dependencies

| ID | Assumption |
|---|---|
| ASM-001 | Target media uses FAT32, exFAT, NTFS, or ext2/3/4 filesystems |
| ASM-002 | ClamAV and YARA signature databases fit within available storage with headroom for history |
| ASM-003 | Device has reliable Wi-Fi access for signature updates (no offline update path in v1) |
| ASM-004 | Operator has physical access to insert/remove media |
| ASM-005 | USB host port provides sufficient power for USB flash drives and low-power portable SSDs; USB HDD support is out of scope for v1 |
| DEP-001 | `udev` rules for automatic mount on media insertion |
| DEP-002 | `ntfs-3g` for NTFS read-only access |
| DEP-003 | `libyara`, `clamd` or `clamscan` CLI integration |

### 2.7 Major Hardware Integration Risks

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| RISK-001 | The Triple IPS LCD HAT is designed for Raspberry Pi GPIO/SPI pin mappings, while the Radxa Zero 3W exposes a different SPI/GPIO mapping. | Display bring-up may require custom device-tree overlays, custom userspace SPI/GPIO handling, or HAT pin adaptation. | Treat display driver bring-up as a major hardware integration task in the prototype phase. |
| RISK-002 | The Triple IPS LCD HAT draws approximately 840 mA from 3.3V, and the usable 3.3V header current budget on the Radxa Zero 3W must be validated. | Direct header powering may cause instability if the Radxa 3.3V rail cannot supply the HAT plus board load. | Bench-test voltage stability; add an external 3.3V regulator if required. |
| RISK-003 | The fixed 1 GB RAM model limits concurrent scanning, large archive analysis, and memory-heavy ClamAV/YARA workloads. | Deep scanning and recursive archive extraction may be unreliable in v1. | Limit v1 to Quick Scan and Full Scan; defer Deep Scan to v2. |

---

## 3. Functional Requirements

### 3.1 Device Detection and Mounting

| ID | Requirement |
|---|---|
| FR-001 | The system SHALL detect insertion of USB mass storage devices (flash drives and portable SSDs) within 3 seconds. |
| FR-002 | The system SHALL detect insertion of SD and microSD cards (via USB card reader or dedicated slot) within 3 seconds. |
| FR-003 | The system SHALL mount detected volumes read-only (`-o ro`) without user intervention. |
| FR-004 | The system SHALL support FAT32, exFAT, NTFS, and ext2/3/4 filesystems. |
| FR-005 | The system SHALL display drive information on the left auxiliary display within 2 seconds of successful mount: label, filesystem type, capacity, and USB link speed. |
| FR-006 | The system SHALL reject or safely unmount unsupported filesystems and display an error on the main display. |
| FR-007 | The system SHALL handle drive removal gracefully during idle and during scan (see Section 10). |

### 3.2 Scan Initiation and Modes

| ID | Requirement |
|---|---|
| FR-010 | The system SHALL present a menu on the main display to select scan mode before starting. |
| FR-011 | The system SHALL support **Quick Scan** mode: executables (PE, ELF, Mach-O), Office documents, scripts, and archives. |
| FR-012 | The system SHALL support **Full Scan** mode: all files on the volume. |
| FR-013 | Deep Scan SHALL NOT be supported in v1; it is deferred to v2 due to the fixed 1 GB RAM hardware target. |
| FR-014 | The operator SHALL initiate a scan by selecting a mode and pressing Enter. |
| FR-015 | The operator SHALL cancel an in-progress scan via double-click on the Enter button; cancellation SHALL complete within 5 seconds. |
| FR-016 | Only one scan SHALL run at a time. |

### 3.3 Scanning Engine

| ID | Requirement |
|---|---|
| FR-020 | The system SHALL scan files using ClamAV signature matching. |
| FR-021 | The system SHALL scan files using YARA rule matching. |
| FR-022 | The system SHALL allow ClamAV's built-in archive scanning in v1, using configured resource limits. The system SHALL NOT implement custom recursive archive extraction in v1. |
| FR-023 | The system SHALL compute SHA-256 hashes of scanned files for report inclusion (not reputation lookup in v1). |
| FR-024 | The system SHALL track and report scan throughput in MB/s on the right auxiliary display. |
| FR-025 | The system SHALL identify the current analysis stage: idle, enumerating, hashing, ClamAV, and YARA. |
| FR-026 | Scanning SHALL continue when no UI client is connected to the API. |

### 3.4 Progress and Status Reporting

| ID | Requirement |
|---|---|
| FR-030 | The main display SHALL show the current file path being analyzed. |
| FR-031 | The main display SHALL show files scanned / total files and estimated time remaining (ETA). |
| FR-032 | The main display SHALL render a segmented progress/status indicator; exact layout is TBD for the 240×240 HAT main display. |
| FR-033 | Filled progress segments SHALL correspond to scan completion percentage; exact segment count is TBD during UI design. |
| FR-034 | Threat Meter segment colors SHALL indicate scan stage: green (normal/ClamAV), blue (hashing), purple (YARA), orange (suspicious/extended analysis), red (malware detected). |
| FR-035 | When malware is detected, all filled Threat Meter segments SHALL immediately change to red and a warning icon SHALL appear at the top of the meter. |
| FR-036 | The right auxiliary display SHALL persistently show: engine name, threat count, current stage, scan speed, and overall status (CLEAN / THREAT FOUND / SCANNING). |
| FR-037 | The system SHALL broadcast real-time progress events via WebSocket to connected clients. |

### 3.5 Threat Detection and User Response

| ID | Requirement |
|---|---|
| FR-040 | When malware or a suspicious match is detected, the system SHALL immediately update all displays and emit a WebSocket alert. |
| FR-041 | The system SHALL present the operator with a decision prompt: continue scanning, stop scan, or view threat details. |
| FR-042 | Because all mounts are read-only (FR-003), the system SHALL NOT offer quarantine or delete actions on the source media in v1. |
| FR-043 | The system SHALL optionally copy detected file metadata and hash to an internal quarantine log on the appliance storage (not the source drive). |
| FR-044 | The system SHALL continue scanning remaining files if the operator chooses "continue" after a detection. |
| FR-045 | The system SHALL record every detection with: file path, engine, signature/rule name, timestamp, and SHA-256 hash. |

### 3.6 Reports and History

| ID | Requirement |
|---|---|
| FR-050 | Upon scan completion (or cancellation), the system SHALL generate a TXT report and an HTML report. |
| FR-051 | Reports SHALL include: device label, serial/volume ID, filesystem, scan mode, start/end time, duration, files scanned, threats found, throughput, and per-threat details. |
| FR-052 | The system SHALL retain scan history without a fixed count limit; retention is bounded only by available internal storage. |
| FR-053 | When internal storage reaches 90% capacity, the system SHALL warn the administrator via Web UI and display. |
| FR-054 | When internal storage reaches 95% capacity, the system SHALL prevent new scans until space is freed. |
| FR-055 | The operator SHALL browse scan history from the device menu and Web UI. |
| FR-056 | Reports SHALL be exportable via Web UI download and REST API. |

### 3.7 Signature Updates

| ID | Requirement |
|---|---|
| FR-060 | The system SHALL update ClamAV and YARA signature databases over Wi-Fi. |
| FR-061 | The system SHALL support manual update initiation from the device menu and Web UI. |
| FR-062 | The system SHALL support scheduled automatic updates (configurable interval, default: daily at 03:00). |
| FR-063 | The system SHALL verify update package integrity before applying. |
| FR-064 | The system SHALL report update status (last update time, database version, success/failure) on the Web UI. |
| FR-065 | Scanning SHALL NOT be available while a database update is in progress. |

### 3.8 Configuration and Administration

| ID | Requirement |
|---|---|
| FR-070 | The system SHALL provide a Web UI accessible on the local network for configuration, history review, and report download. |
| FR-071 | The system SHALL expose a REST API for all scan, history, configuration, and update operations. |
| FR-072 | The system SHALL expose a WebSocket endpoint for live scan progress and alert streaming. |
| FR-073 | The system SHALL provide SSH access for administrator debugging and maintenance. |
| FR-074 | The operator SHALL configure Wi-Fi credentials via the device menu (onboarding) or Web UI. |
| FR-075 | The system SHALL persist configuration across reboots. |

### 3.9 Physical Input

| ID | Requirement |
|---|---|
| FR-080 | Button 1 (Down) SHALL navigate menu items downward. |
| FR-081 | Button 2 (Enter) SHALL confirm the selected menu item or action. |
| FR-082 | Long-press Enter (> 1.5 s) SHALL navigate back to the previous menu level. |
| FR-083 | Double-click Enter (two presses within 400 ms) SHALL cancel an in-progress scan. |

### 3.10 Archive Scanning

| ID | Requirement |
|---|---|
| FR-090 | The system SHALL accept standalone archive files (ZIP, 7z, RAR) as scan targets when presented on a mounted volume or internal storage. |
| FR-091 | Archive handling SHALL respect the read-only policy; only ClamAV's built-in archive handling is permitted in v1. |
| FR-092 | If temporary files are created by ClamAV or scanner tooling, they SHALL be stored on internal microSD storage and removed after scan completion. |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement |
|---|---|
| NFR-001 | USB 3.0 devices SHALL sustain scan throughput ≥ 50 MB/s for Quick Scan on the Radxa Zero 3W. |
| NFR-002 | UI updates (display refresh) SHALL occur at ≥ 2 Hz during active scanning. |
| NFR-003 | WebSocket event latency from engine to client SHALL be ≤ 500 ms. |
| NFR-004 | Device boot to ready state SHALL complete within 30 seconds. |
| NFR-005 | Drive detection to mount-complete SHALL complete within 5 seconds. |

### 4.2 Reliability

| ID | Requirement |
|---|---|
| NFR-010 | The system SHALL recover from scan engine crash and return to idle within 10 seconds. |
| NFR-011 | An incomplete scan (power loss, crash) SHALL be recorded in history with status `INTERRUPTED`. |
| NFR-012 | The system SHALL run continuously for 72 hours without memory leak-induced failure. |

### 4.3 Usability

| ID | Requirement |
|---|---|
| NFR-020 | Scan result (CLEAN / THREAT FOUND) SHALL be readable on the fixed display hardware at normal handheld/desktop viewing distance. |
| NFR-021 | Threat Meter progress SHALL be readable on the 1.3-inch main display; exact layout and readability target are TBD during UI design. |
| NFR-022 | A first-time operator SHALL complete a scan with no instructions beyond on-device menu labels. |
| NFR-023 | All on-device UI text SHALL be in English for v1. |

### 4.4 Maintainability

| ID | Requirement |
|---|---|
| NFR-030 | Scan engine logs SHALL use structured JSON format with rotation (max 100 MB per file, 5 files retained). |
| NFR-031 | Software updates SHALL be deployable via SSH without re-flashing the OS (package or image update). |
| NFR-032 | API endpoints SHALL be documented in OpenAPI 3.0 format. |

### 4.5 Portability

| ID | Requirement |
|---|---|
| NFR-040 | The scan engine SHALL have no dependency on a specific UI framework; it runs as a systemd service. |
| NFR-041 | Display rendering (LVGL) SHALL be a separate process communicating via the local API. |

### 4.6 Resource Constraints

| ID | Requirement |
|---|---|
| NFR-050 | Peak RAM usage during v1 Quick Scan and Full Scan SHALL not exceed 80% of available memory on the fixed 1 GB Radxa Zero 3W target. |
| NFR-051 | Internal storage budget: OS + engines ≤ 4 GB on the fixed 32 GB microSD card; remaining space is reserved for signatures, history, reports, and scanner temporary files. |

---

## 5. User Interface Specification

### 5.1 Display Layout Overview

The v1 display hardware is fixed to the Waveshare Zero LCD HAT (A) / Triple IPS LCD HAT. The exact v1 UI layout is **TBD** and must be redesigned for the small display sizes.

```
┌──────────────────────────────┐
│ 0.96" AUX      1.3" MAIN     │
│ 160×80         240×240       │
│ ST7735S        ST7789        │
│                              │
│              0.96" AUX       │
│              160×80          │
│              ST7735S         │
└──────────────────────────────┘
```

### 5.2 Main Display — Threat Meter Specification

The Threat Meter remains a product concept, but its exact form is TBD for the 240×240 main screen.

| Property | Value |
|---|---|
| Segments | TBD during UI design |
| Position | TBD during UI design |
| Fill direction | Bottom to top |
| Mapping | Filled segments SHALL be proportional to scan completion percentage |
| Min segment size | TBD during UI design |

#### 5.2.1 Color States

| State | Color | RGB (approx.) | Trigger |
|---|---|---|---|
| Normal scan | Green | `#00C853` | Default during ClamAV scanning |
| Hashing | Blue | `#2979FF` | SHA-256 computation in progress |
| YARA | Purple | `#AA00FF` | YARA rule evaluation in progress |
| Suspicious | Orange | `#FF6D00` | Extended analysis of flagged file |
| Malware found | Red | `#D50000` | Threat detected; all filled segments turn red |
| Empty segment | Dark gray | `#333333` | Not yet reached |

#### 5.2.2 Malware Detection Behavior

When a threat is detected during an active scan:

1. All currently filled segments instantly change from their stage color to **red**.
2. A warning icon (⚠ or equivalent glyph) appears at the top of the Threat Meter column.
3. The right auxiliary display status changes to **THREAT FOUND** with threat count.
4. The main display text area shows the detected file path and signature name.
5. The filled segments remain red for the duration of the scan (they do not revert to green).

### 5.3 Main Display — Text Area Content by State

| State | Content |
|---|---|
| Idle (no media) | `Insert a drive to begin` |
| Media detected | Drive summary + `Press Enter to scan` |
| Menu | Scan mode selection list with cursor |
| Scanning | `Scanning...`, current file path (truncated with ellipsis if needed), `Files: N / M`, `ETA: MM:SS` |
| Threat prompt | Threat details + action choices (Continue / Stop / Details) |
| Complete | `Scan complete` + result summary + `Press Enter for menu` |
| Error | Error description + suggested action |

### 5.4 Left Auxiliary Display — Drive Info

| Field | Source | Update Trigger |
|---|---|---|
| Label | Volume label or `Unknown` | Mount event |
| Filesystem | `FAT32`, `exFAT`, `NTFS`, `ext4`, etc. | Mount event |
| Capacity | Total size formatted (e.g., `931 GB`) | Mount event |
| USB Speed | `USB 2.0`, `USB 3.0`, `USB 3.1` | Mount event |
| Status icon | Connected / Removed / Error | Mount/unmount events |

This display content is **persistent** and does not change during scanning (except status icon on removal).

### 5.5 Right Auxiliary Display — Security Status

| Field | Source | Update Trigger |
|---|---|---|
| Engine | `ClamAV` + `YARA` | Scan start |
| Threats | Integer count | Real-time during scan |
| Speed | Current throughput (e.g., `72 MB/s`) | Real-time during scan |
| Stage | Current analysis stage | Real-time during scan |
| Status | `CLEAN` / `SCANNING` / `THREAT FOUND` / `ERROR` | State change |

When status is `CLEAN` after scan completion, display a large green checkmark with `✔ CLEAN`.
When status is `THREAT FOUND`, display a large red warning with threat count.

### 5.6 Typography and Visual Design

| Property | Specification |
|---|---|
| Background | Dark (`#1A1A2E` or similar) |
| Primary text | White (`#FFFFFF`) |
| Secondary text | Light gray (`#B0B0B0`) |
| Font | Monospace or clean sans-serif; minimum 12 px body, 24 px status |
| Aesthetic | Industrial / laboratory instrument; high contrast; no decorative elements |
| Color | Full color displays; color used functionally (Threat Meter, status indicators) |

### 5.7 Button Interaction Map

| Input | Context | Action |
|---|---|---|
| Down (Btn 1) | Menu | Move cursor down |
| Down (Btn 1) | Scanning | No action |
| Enter (Btn 2) | Menu | Select item |
| Enter (Btn 2) | Idle + media | Open scan mode menu |
| Enter (Btn 2) | Threat prompt | Confirm selected action |
| Long-press Enter | Any menu | Go back one level |
| Double-click Enter | Scanning | Cancel scan |

---

## 6. Hardware Requirements

### 6.1 Compute Platform

| Component | Specification |
|---|---|
| Board | Radxa Zero 3W |
| SoC | Rockchip RK3566 (quad-core Cortex-A55, up to 1.6 GHz on Radxa Zero 3W) |
| RAM | Fixed 1 GB LPDDR4; no future hardware upgrade assumed |
| Storage | Fixed 32 GB microSD card only; no eMMC dependency |
| Wi-Fi | Onboard 802.11 b/g/n/ac |
| USB | USB 3.0 OTG (host mode for scanning) + USB 2.0 |
| GPIO | For buttons and display interfaces |

### 6.2 Displays

| Display | Role | Size / Resolution | Interface |
|---|---|---|---|
| Main | Task + progress/status indicator | 1.3", 240×240, ST7789 | SPI via Triple IPS LCD HAT |
| Aux 1 | Drive info / TBD compact status | 0.96", 160×80, ST7735S | SPI via Triple IPS LCD HAT |
| Aux 2 | Security info / TBD compact status | 0.96", 160×80, ST7735S | SPI via Triple IPS LCD HAT |

All displays MUST use the fixed Triple IPS LCD HAT hardware. Final field allocation between the three displays is TBD.

### 6.3 Input

| Component | Specification |
|---|---|
| Button 1 | Momentary push, GPIO with hardware debounce |
| Button 2 | Momentary push, GPIO with hardware debounce |

### 6.4 Power

| Component | Specification |
|---|---|
| Input | USB-C 5V/3A |
| Consumption | Estimated 4W idle with displays on; 6–10W typical during scanning depending on USB media |

### 6.5 Enclosure

| Property | Specification |
|---|---|
| Material | ABS or aluminum |
| Mounting | Desktop stand or portable form factor |
| Drive access | Front or side USB-A port(s) |
| Ventilation | Passive vents adequate for continuous operation |

### 6.6 Not Included in v1

- RGB status LED
- Piezo buzzer
- Vibration motor
- Battery (stretch goal — see Section 12)
- Barcode/QR scanner
- RFID/NFC reader
- Current sensor / live per-rail power measurement

---

## 7. Software Architecture

### 7.1 Architecture Overview

The system follows an **API-first, multi-client** architecture. The scan engine runs as a headless systemd service; all user interfaces are clients.

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ LVGL Display │  │ Web UI       │  │ Android App (v2) │   │
│  │ Manager      │  │ (Browser)    │  │                  │   │
│  │ (3 displays) │  │              │  │                  │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                 │                    │              │
│         └─────────┬───────┴────────────────────┘              │
│                   │ REST + WebSocket                          │
│         ┌─────────▼──────────────────────────┐               │
│         │         Scan Engine API             │               │
│         │  (FastAPI + WebSocket, port 8080)   │               │
│         └─────────┬──────────────────────────┘               │
│                   │                                           │
│         ┌─────────▼──────────────────────────┐               │
│         │         Scan Engine Core            │               │
│         │  ┌─────────┐ ┌────────┐ ┌───────┐  │               │
│         │  │ Mount   │ │Scanner │ │Report │  │               │
│         │  │ Manager │ │Pipeline│ │Writer │  │               │
│         │  └─────────┘ └────────┘ └───────┘  │               │
│         └─────────┬──────────────────────────┘               │
│                   │                                           │
│    ┌──────────────┼──────────────┐                           │
│    ▼              ▼              ▼                           │
│ ┌──────┐   ┌──────────┐   ┌──────────┐                      │
│ │udev/ │   │ ClamAV   │   │ SQLite   │                      │
│ │mount │   │ + YARA   │   │ History  │                      │
│ └──────┘   └──────────┘   └──────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Component Descriptions

| Component | Language | Responsibility |
|---|---|---|
| **scan-engine** | Python 3 | Core service: mount management, file enumeration, scanning pipeline, report generation, history persistence |
| **scan-api** | Python 3 (FastAPI) | REST endpoints + WebSocket event stream; runs in-process with scan-engine or as WSGI/ASGI wrapper |
| **display-manager** | Python 3 + LVGL | Renders UI on three independent displays; subscribes to WebSocket for real-time updates; handles button GPIO input |
| **web-ui** | HTML/JS (static) | Served by scan-api; configuration, history browser, report download |
| **update-manager** | Python 3 | ClamAV `freshclam` + YARA rule sync over Wi-Fi |

### 7.3 Process Model

| Process | systemd Unit | Priority |
|---|---|---|
| scan-engine (+ API) | `portable-av-engine.service` | Runs always |
| display-manager | `portable-av-display.service` | Runs always; restarts on crash |
| freshclam | `clamav-freshclam.service` | On-demand / scheduled |

### 7.4 Data Storage

| Store | Technology | Contents |
|---|---|---|
| Configuration | JSON file (`/etc/portable-av/config.json`) | Wi-Fi, update schedule, scan defaults |
| Scan history | SQLite (`/var/lib/portable-av/history.db`) | All scan records |
| Reports | Filesystem (`/var/lib/portable-av/reports/`) | TXT + HTML per scan |
| Temp extraction | tmpfs (`/tmp/portable-av/`) | Archive extraction workspace; cleared after each scan |
| Signature DB | ClamAV + YARA default paths | Managed by update-manager |

### 7.5 API Endpoints (Summary)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/status` | Engine status, version, uptime |
| GET | `/api/v1/drive` | Current mounted drive info |
| POST | `/api/v1/scan` | Start scan `{ "mode": "quick\|full" }` |
| DELETE | `/api/v1/scan` | Cancel active scan |
| GET | `/api/v1/scan/progress` | Current scan progress snapshot |
| WS | `/api/v1/scan/events` | Real-time progress + alert stream |
| GET | `/api/v1/history` | List past scans (paginated) |
| GET | `/api/v1/history/{id}` | Scan detail |
| GET | `/api/v1/history/{id}/report.{txt,html}` | Download report |
| POST | `/api/v1/update` | Trigger signature update |
| GET | `/api/v1/config` | Read configuration |
| PUT | `/api/v1/config` | Update configuration |

Full OpenAPI specification to be produced in the HLD phase.

### 7.6 GUI Framework Selection Rationale

| Surface | Framework | Rationale |
|---|---|---|
| Embedded displays | **LVGL** | Lightweight, purpose-built for embedded SPI displays; direct framebuffer control; low CPU overhead; independent of network stack |
| Web UI | Static HTML + vanilla JS (or lightweight framework) | Zero install; served by existing API; accessible from any browser |
| Android app (v2) | Kotlin + Jetpack Compose | Native performance; consumes REST + WebSocket API; no shared UI code needed |

LVGL is recommended over Pygame because it is designed for resource-constrained embedded targets, supports multiple display instances, and keeps the display manager decoupled from the scan engine. Pygame would couple rendering to a heavier runtime with no benefit for fixed-layout industrial UI.

---

## 8. State Machine

### 8.1 Engine States

```
                    ┌──────────┐
         boot ─────►│  BOOT    │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
              ┌────►│  IDLE    │◄────────────────┐
              │     └────┬─────┘                 │
              │          │ media inserted        │
              │     ┌────▼──────┐                 │
              │     │  MOUNTED  │                 │
              │     └────┬──────┘                 │
              │          │ user selects scan      │
              │     ┌────▼──────┐                 │
              │     │  MENU     │                 │
              │     └────┬──────┘                 │
              │          │ scan started           │
              │     ┌────▼──────┐    threat       │
              │     │ SCANNING  │──────────┐      │
              │     └────┬──────┘          │      │
              │          │          ┌────▼─────┐  │
              │          │          │ THREAT   │  │
              │          │          │ PROMPT   │  │
              │          │          └────┬─────┘  │
              │          │               │        │
              │     ┌────▼──────┐         │        │
              │     │ COMPLETE  │         │        │
              │     └────┬──────┘         │        │
              │          │               │        │
              │     ┌────▼──────┐         │        │
              └─────┤  IDLE     │◄────────┘        │
                    └───────────┘   media removed  │
                         │                         │
                    ┌────▼─────┐                    │
                    │  ERROR   │────────────────────┘
                    └──────────┘   recover
```

### 8.2 State Transition Table

| From | Event | To | Actions |
|---|---|---|---|
| BOOT | Services ready | IDLE | Initialize displays, start API |
| IDLE | USB/SD inserted | MOUNTED | Mount ro, update left aux display |
| IDLE | No media | IDLE | Show "Insert a drive" |
| MOUNTED | Enter pressed | MENU | Show scan mode menu |
| MOUNTED | Media removed | IDLE | Unmount, clear drive display |
| MENU | Mode selected + Enter | SCANNING | Begin enumeration + scan pipeline |
| MENU | Long-press Enter | MOUNTED | Return to drive ready |
| SCANNING | Scan finished | COMPLETE | Generate reports, update history |
| SCANNING | Threat detected | THREAT_PROMPT | Alert displays, pause for user input |
| SCANNING | Double-click Enter | COMPLETE | Cancel scan, save partial report |
| SCANNING | Media removed | ERROR | Abort scan, log error |
| THREAT_PROMPT | Continue | SCANNING | Resume pipeline |
| THREAT_PROMPT | Stop | COMPLETE | Finalize with threats found |
| THREAT_PROMPT | Details | THREAT_PROMPT | Show threat info (scrollable) |
| COMPLETE | Enter pressed | MENU | Allow re-scan or new mode |
| COMPLETE | Media removed | IDLE | Unmount, clear displays |
| ERROR | Recoverable fault | IDLE | Display error, log event |
| ERROR | Media re-inserted | MOUNTED | Re-mount |

### 8.3 Threat Meter State During Scan

| Scan Stage | Meter Color | Right Aux Stage Field |
|---|---|---|
| Enumerating | Green | `Enumerating` |
| Hashing | Blue | `Hashing` |
| ClamAV scan | Green | `ClamAV` |
| YARA scan | Purple | `YARA` |
| Archive extraction | Orange | `Extracting` |
| Suspicious file analysis | Orange | `Analyzing` |
| Threat detected | Red (all filled) | `THREAT FOUND` |

---

## 9. Security Requirements

| ID | Requirement |
|---|---|
| SEC-001 | All external media MUST be mounted read-only. The mount manager SHALL refuse read-write mount requests. |
| SEC-002 | The scan engine SHALL NOT execute files from scanned media. |
| SEC-003 | If scanner tooling creates temporary files, they SHALL be stored in an isolated temp directory with no execute permissions. |
| SEC-004 | SSH access SHALL require key-based authentication; password login SHALL be disabled. |
| SEC-005 | The Web UI and REST API SHALL require authentication (token-based) for all write operations. |
| SEC-006 | The Web UI and REST API MAY allow unauthenticated read of scan status on the local network (configurable). |
| SEC-007 | Signature updates SHALL be downloaded over HTTPS with certificate verification. |
| SEC-008 | The appliance SHALL NOT automatically forward scan data to external services. |
| SEC-009 | Scanner temporary files SHALL be removed after scan completion. |
| SEC-010 | The scan engine process SHALL run as an unprivileged user (`portable-av`), not root. Mount operations via `udev` + `pmount` or polkit. |
| SEC-011 | Report files SHALL be readable only by the `portable-av` user and administrators. |
| SEC-012 | The system SHALL log all authentication attempts and scan operations. |

---

## 10. Error Handling

### 10.1 Error Categories

| Category | Examples | User-Facing Behavior |
|---|---|---|
| Mount failure | Unsupported FS, corrupted superblock | Error on main display; left aux shows `Error` status |
| Media removal | Drive unplugged during scan | Abort scan; main display: `Drive removed during scan` |
| Engine failure | ClamAV crash, OOM | Auto-restart engine; display: `Scanner error — retrying` |
| Scan timeout | Single file > 120 s | Skip file, log warning, continue scan |
| Storage full | Internal storage ≥ 95% | Block new scans; Web UI warning |
| Network failure | Wi-Fi down during update | Display update failure; retry on schedule |
| Archive error | Corrupt archive, password-protected | Skip archive, log in report, continue scan |

### 10.2 Error Display Rules

1. Errors on the main display use red text with a brief description and one suggested action.
2. The right auxiliary display status changes to `ERROR`.
3. Transient errors (auto-recoverable) display for 5 seconds then clear.
4. Persistent errors require user acknowledgment (Enter press).

### 10.3 Logging

All errors SHALL be logged with: timestamp, severity, component, error code, message, and contextual metadata (drive label, file path if applicable).

---

## 11. Acceptance Criteria

### 11.1 Core Scanning

| # | Test | Pass Criteria |
|---|---|---|
| AC-001 | Insert FAT32 USB flash drive | Mounted ro within 5 s; drive info on left aux |
| AC-002 | Quick Scan clean drive | Result `CLEAN`; TXT + HTML reports generated |
| AC-003 | Full Scan NTFS portable SSD | All files enumerated and scanned; throughput ≥ 50 MB/s |
| AC-004 | Deep Scan unavailable in v1 | UI and API do not offer `deep` scan mode |
| AC-005 | EICAR test file detection | Threat detected; meter turns red; prompt shown |
| AC-006 | Cancel scan (double-click Enter) | Scan stops within 5 s; partial report saved |

### 11.2 User Interface

| # | Test | Pass Criteria |
|---|---|---|
| AC-010 | Threat Meter at 50% | Approximately half of the UI-defined segments are filled, green |
| AC-011 | Stage color change | Meter turns blue during hashing, purple during YARA |
| AC-012 | Threat detection visual | All filled segments turn red; warning icon appears |
| AC-013 | CLEAN status | Clean status is clearly visible on the fixed display hardware at normal handheld/desktop viewing distance |
| AC-014 | Menu navigation | Down + Enter selects mode; long-press Enter goes back |

### 11.3 API and Networking

| # | Test | Pass Criteria |
|---|---|---|
| AC-020 | REST API scan trigger | `POST /api/v1/scan` starts scan; progress via WebSocket |
| AC-021 | Web UI access | Configuration and history pages load in browser |
| AC-022 | SSH access | Key-based login succeeds; password login rejected |
| AC-023 | Scan without display client | Scan completes with displays connected but API not polled |

### 11.4 Data and Updates

| # | Test | Pass Criteria |
|---|---|---|
| AC-030 | Scan history persistence | Previous scans visible after reboot |
| AC-031 | Report download | TXT and HTML downloadable via API and Web UI |
| AC-032 | Wi-Fi signature update | ClamAV + YARA databases updated successfully |
| AC-033 | Storage limit warning | Warning displayed at 90% internal storage usage |

### 11.5 Security

| # | Test | Pass Criteria |
|---|---|---|
| AC-040 | Read-only verification | `mount` shows `ro` for all external volumes |
| AC-041 | No file execution | Executable on media is scanned but never executed |
| AC-042 | Temp cleanup | No files remain in temp directory after scan |

---

## 12. Future Enhancements

The following features are **out of scope for v1** but documented for roadmap planning.

### 12.1 v2 — Enhanced Detection Engines

| Feature | Description |
|---|---|
| SHA-256 reputation database | Lookup file hashes against known-good/known-bad databases |
| Heuristic analyzer | Behavioral and structural heuristics beyond signature matching |
| Office macro detector | Specialized analysis of VBA/macros in Office documents |
| Hidden executable detector | Flag files with mismatched extension and magic bytes |
| Double-extension detector | Flag `file.pdf.exe` patterns |
| PE metadata analyzer | Inspect Windows PE headers, imports, sections |
| ELF analyzer | Inspect Linux ELF binaries |
| Script analyzer | Static analysis of PowerShell, JS, VBS, BAT |

### 12.2 v2 — Platform Extensions

| Feature | Description |
|---|---|
| Android companion app | Native app consuming REST + WebSocket API |
| Additional report formats | JSON, PDF, CSV |
| Custom scan mode | User-defined file type and path filters |
| Offline signature update | USB package-based database update |
| Multi-language UI | Localized on-device and web interfaces |
| Password-protected settings | Prevent unauthorized configuration changes |
| Deep Scan | Full scan plus nested archive extraction and heavier analysis, subject to memory validation |

### 12.3 v3 — Hardware and Enterprise

| Feature | Description |
|---|---|
| Battery level display | Show charge status on auxiliary display (requires battery hardware) |
| Secure boot + signed updates | Verified boot chain and cryptographically signed firmware/packages |
| Wi-Fi report export | Push reports to network destination or cloud |
| Barcode/QR drive identification | Scan barcode on drive label to tag scan history |
| RFID/NFC drive ownership | Associate drives with owners via NFC tag |
| Duplicate file detection | Identify identical files across scans |
| Hash comparison | Compare file hashes against previous scans of same drive |
| Incremental scan | Scan only new or modified files since last scan |
| Network share scanning | SMB/CIFS remote volume scanning |
| iPhone / Android MTP | Mobile device media scanning |

---

## Appendix A — Requirement Traceability Matrix (Summary)

| Requirement | Design Phase | Implementation | Test |
|---|---|---|---|
| FR-001–007 | HLD: Mount Manager | `mount_manager.py` | AC-001 |
| FR-010–016 | HLD: Scan Controller | `scan_controller.py` | AC-001–006 |
| FR-020–026 | HLD: Scanner Pipeline | `scanner/` | AC-002–005 |
| FR-030–037 | UI Spec §5 | `display_manager/` | AC-010–013 |
| FR-040–045 | HLD: Threat Handler | `threat_handler.py` | AC-005 |
| FR-050–056 | HLD: Report Writer | `report_writer.py` | AC-030–031 |
| FR-060–065 | HLD: Update Manager | `update_manager.py` | AC-032 |
| FR-070–075 | HLD: API | `scan_api/` | AC-020–022 |
| FR-080–083 | UI Spec §5.7 | `input_handler.py` | AC-014 |
| SEC-001–012 | HLD: Security | Platform config | AC-040–042 |

---

## Appendix B — Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-07-09 | — | Initial SRS based on requirements gathering session |
| 1.1 | 2026-07-09 | — | OS baseline: Armbian Ubuntu 24.04 Noble Minimal, vendor kernel 6.1.115 |

---

*End of Document*
