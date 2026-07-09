# Implementation Plan

## Portable Antivirus Appliance

| Field | Value |
|---|---|
| **Document ID** | PLAN-PAV-001 |
| **Version** | 0.1 |
| **Date** | 2026-07-09 |
| **Status** | Initial implementation plan |
| **Source Requirements** | `SRS.md` v1.1 |
| **Source Architecture** | `HLD.md` v1.1 |
| **Source Design** | `LLD.md` v0.2 |
| **Target Hardware** | Radxa Zero 3W, 1 GB LPDDR4, 32 GB microSD, Waveshare Zero LCD HAT (A) |
| **Target OS** | Armbian Ubuntu 24.04 Noble Minimal (CLI), vendor kernel 6.1.115 |

---

## 1. Purpose

This plan converts the approved SRS, HLD, and LLD into an ordered implementation path. It starts with the work that can be completed before the display HAT arrives, then adds hardware bring-up, display integration, and end-to-end appliance validation.

The display HAT is expected in approximately 3 days. Until then, implementation focuses on the headless foundation: OS bring-up, scan engine, read-only mount flow, persistence, reports, REST API, WebSocket events, and a simulated display client.

---

## 2. Planning Assumptions

- The fixed target board is Radxa Zero 3W with 1 GB RAM and 32 GB microSD.
- The OS baseline is Armbian Ubuntu 24.04 Noble Minimal (CLI), vendor kernel 6.1.115.
- v1 scan modes are Quick Scan and Full Scan only.
- v1 engines are ClamAV and YARA.
- v1 archive handling uses ClamAV built-in archive scanning only.
- All removable media is mounted read-only.
- Source media is never quarantined, deleted, or modified.
- Display-specific work can use a simulator until the HAT arrives.
- `clamd` is the default design target, with `clamscan` fallback preserved until Radxa benchmarks are complete.

---

## 3. Open Decisions and Gates

No open decision blocks starting implementation. The items below are planned validation gates.

| Gate | Decision | Current Default | Resolution Point |
|---|---|---|---|
| GATE-001 | Display pin map and SPI assignment | Provisional HLD mapping | Display HAT bring-up |
| GATE-002 | Python SPI/GPIO library | `spidev` plus Radxa-compatible GPIO library TBD | Display HAT bring-up |
| GATE-003 | HAT 3.3V power sufficiency | Board 3.3V rail assumed sufficient | Display HAT power test |
| GATE-004 | ClamAV mode | `clamd` preferred, `clamscan` fallback | Headless scan benchmark |
| GATE-005 | Progress percentage strategy | Streaming enumeration; optional pre-count | Real-media scan UX benchmark |
| GATE-006 | Threat meter segment count | 12 segments | Display visual review |

If a gate fails, update `LLD.md` §19.1 and the affected configuration defaults before continuing dependent work.

---

## 4. Phase Overview

| Phase | Name | Can Start Now | Primary Output |
|---|---|---|---|
| P0 | Project Skeleton and Dev Tooling | Yes | Python package, config, install layout |
| P1 | Target OS and Board Foundation | Yes | Radxa boots, SSH works, required packages installed |
| P2 | Headless Scan Core | Yes | Scan controller, ClamAV/YARA, reports, history |
| P3 | Read-Only Mount Flow | Yes | udev/systemd mount helper, read-only media handling |
| P4 | REST API and WebSocket | Yes | Local/LAN API for scan control and progress |
| P5 | Display Simulator | Yes | Terminal/mock display and button client |
| P6 | Display HAT Bring-Up | After HAT arrives | Validated SPI/GPIO/power/pin map |
| P7 | Integrated Appliance Loop | After P2-P6 | Button-driven end-to-end scanner |
| P8 | Hardening and Acceptance | After integration | v1 prototype acceptance pass |

---

## 5. Three-Day Headless Sprint

### Day 1: OS, Skeleton, and Local Scaffolding

Goal: make the project runnable on development machine and target board.

Tasks:

- Flash Armbian Ubuntu 24.04 Noble Minimal vendor image to 32 GB microSD.
- Configure hostname, admin user, SSH key, Wi-Fi client mode, timezone, and locale.
- Confirm SSH login and disable password login.
- Install base packages: Python 3, `venv`, `pip`, ClamAV, YARA, SQLite, `exfatprogs`, `ntfs-3g`, `udev`, `systemd` tooling.
- Create Python package skeleton from `LLD.md` §4.
- Add default config file template for `/etc/portable-av/config.json`.
- Add local development config under `config/dev.config.json`.
- Add initial logging setup.
- Add SQLite migration/bootstrap module.
- Add placeholder `install.sh` with directory creation and system user setup steps.

Deliverables:

- `portable_av/` package exists and imports cleanly.
- `python -m portable_av.api.app` or equivalent dev entry point starts.
- SQLite database can be created locally.
- Target board is reachable over SSH.

Exit checks:

- `python -m compileall portable_av` passes.
- Config validation accepts default config.
- Radxa reports vendor kernel 6.1.115.

### Day 2: Headless Scan Engine

Goal: scan files without display hardware.

Tasks:

- Implement core enums and dataclasses/Pydantic models.
- Implement `FileEnumerator` with Quick Scan extension filter.
- Implement `ClamAvAdapter` with output parsing and timeout handling.
- Implement `YaraAdapter` with rule compilation, scan, and last-known-good behavior.
- Implement `HistoryRepository` methods for scans, detections, events, and signature updates.
- Implement `ScanController` state transitions for `IDLE`, `MOUNTED`, `SCANNING`, `THREAT_PROMPT`, `COMPLETE`, and `ERROR`.
- Implement cancellation and threat action handling.
- Implement `ReportWriter` for TXT and HTML.
- Add EICAR fixture procedure for validation.

Deliverables:

- A CLI/dev path can run Quick Scan against a local fixture directory.
- EICAR detection is recorded.
- TXT and HTML reports are generated.
- History persists after restart.

Exit checks:

- Clean fixture reports `CLEAN`.
- EICAR fixture reports threat.
- Cancelled scan writes partial report.
- No source file is modified during scan.

### Day 3: Mount, API, Events, and Simulator

Goal: prove the appliance behavior headlessly.

Tasks:

- Implement mount device inspection using `lsblk`/`blkid`.
- Implement read-only mount helper and unmount flow.
- Draft `udev` rule and `portable-av-mount@.service`.
- Implement internal drive notification endpoint.
- Implement FastAPI app factory and dependency providers.
- Implement REST endpoints for status, drive, scan start/cancel/progress, history, reports, config, and updates.
- Implement bearer-token auth for write endpoints.
- Implement in-process `EventBus`.
- Implement WebSocket event stream.
- Implement display simulator that renders main, aux-left, and aux-right state in terminal.
- Implement simulated button actions through keyboard or REST calls.

Deliverables:

- USB flash drive mounts read-only.
- API can start/cancel Quick Scan.
- WebSocket emits progress and threat events.
- Simulator shows scan state, progress, and threat prompt.

Exit checks:

- `mount` shows `ro,nosuid,nodev,noexec` for external media.
- `POST /api/v1/scan` starts a scan.
- `DELETE /api/v1/scan` cancels within 5 seconds.
- WebSocket receives `scan_started`, `scan_progress`, `threat_detected`, and `scan_completed`.
- TXT/HTML reports are downloadable through API.

---

## 6. Display Arrival Plan

### Day 4: Display HAT Bring-Up

Goal: close display hardware gates.

Tasks:

- Inspect HAT pinout against Radxa header mapping.
- Enable SPI3 overlay using `rsetup` or `/boot/armbianEnv.txt`.
- Verify `/dev/spidev*` devices exist.
- Test ST7789 main display with static image.
- Test both ST7735S auxiliary displays with static images.
- Validate chip select, reset, data/command, and backlight GPIOs.
- Validate KEY1/KEY2 GPIO events.
- Run all displays active for 30 minutes.
- Check for brownout, reboot, undervoltage, or display corruption.
- Update `config.json` display device mapping.
- Update `LLD.md` open items and sign-off table.

Deliverables:

- Confirmed display pin map.
- Confirmed Python SPI/GPIO library.
- Confirmed power path or regulator requirement.
- Bring-up scripts under `tools/bringup/`.

Exit checks:

- Main display shows test image.
- Both auxiliary displays show test images.
- Buttons produce debounced events.
- System stays stable for 30 minutes with displays active.

---

## 7. Full Implementation Phases

### P0: Project Skeleton and Dev Tooling

Tasks:

- Create package layout from LLD.
- Add Python virtual environment instructions.
- Add dependency file.
- Add config templates.
- Add basic logging and paths helpers.
- Add initial tests folder.

Done when:

- Package imports cleanly.
- Config can be loaded and validated.
- Empty app starts locally.

### P1: Target OS and Board Foundation

Tasks:

- Flash and configure target OS.
- Verify SSH and Wi-Fi.
- Install packages.
- Create `portable-av` user and directories.
- Prepare systemd unit drafts.

Done when:

- Board can run the empty app as a service.
- Required packages are installed.
- SSH key login works and password login is disabled.

### P2: Headless Scan Core

Tasks:

- Implement scan models.
- Implement file enumeration.
- Implement ClamAV adapter.
- Implement YARA adapter.
- Implement scan controller.
- Implement reports.
- Implement SQLite repository.

Done when:

- Quick Scan and Full Scan run against mounted or local fixture paths.
- EICAR detection is reported.
- Reports and history are generated.

### P3: Read-Only Mount Flow

Tasks:

- Implement device inspection.
- Implement filesystem allowlist.
- Implement read-only mount commands.
- Implement unmount handling.
- Implement udev/systemd integration.
- Implement internal engine notification.

Done when:

- FAT32, exFAT, NTFS, and ext volumes mount read-only.
- Unsupported filesystems produce clear errors.
- Media removal is reported without crashing the engine.

### P4: REST API and WebSocket

Tasks:

- Implement app factory.
- Implement API schemas.
- Implement auth.
- Implement scan/status/drive/history/config/update routes.
- Implement WebSocket event stream.
- Add OpenAPI review.

Done when:

- API can run the headless scan prototype.
- WebSocket clients receive live events.
- Write operations require auth.

### P5: Display Simulator

Tasks:

- Implement event-stream client.
- Render main/aux-left/aux-right state in terminal.
- Simulate button navigation.
- Validate threat prompt behavior.

Done when:

- End-to-end scan can be operated without real display hardware.
- UI state transitions are visible and match SRS.

### P6: Real Display Service

Tasks:

- Implement `LcdHatDriver`.
- Implement screen renderers.
- Implement button GPIO input.
- Implement display manager reconnect behavior.
- Convert simulator states into real display frames.

Done when:

- `portable-av-display.service` starts at boot.
- Displays show idle/status/progress/threat states.
- Buttons trigger REST actions.

### P7: Integrated Appliance Loop

Tasks:

- Connect mount events, engine, API, display, and reports.
- Implement threat prompt continue/stop/details across display and API.
- Implement storage threshold enforcement.
- Add Web UI static pages or minimal operational UI.
- Validate scan without browser connected.

Done when:

- Insert drive, choose scan, see progress, detect EICAR, and view report.
- Detection works with no browser or Web UI client connected.

### P8: Hardening and Acceptance

Tasks:

- Run acceptance criteria from `SRS.md` §11.
- Run validation checklist from `HLD.md` §21.
- Tune ClamAV limits.
- Decide `clamd` vs `clamscan`.
- Tune progress strategy.
- Review logs and SD write volume.
- Update SRS/HLD/LLD if validation changes any decision.

Done when:

- Core acceptance criteria pass.
- Validation gates are closed or explicitly deferred.
- Known limitations are documented.

---

## 8. Task Dependency Map

```text
P0 Project Skeleton
  -> P2 Headless Scan Core
  -> P4 API/WebSocket
  -> P5 Display Simulator

P1 Target OS
  -> P3 Read-Only Mount Flow
  -> P2/P4 on target board

Display HAT arrival
  -> P6 Real Display Service
  -> P7 Integrated Appliance Loop

P2 + P3 + P4 + P6
  -> P7 Integrated Appliance Loop
  -> P8 Hardening and Acceptance
```

---

## 9. Verification Plan

### 9.1 Developer Checks

- Import/package check.
- Unit tests for config, enumerator, adapter parsers, repository, scan controller, and API routes.
- Static linting/formatting once project tooling is selected.
- Local fixture scans.

### 9.2 Target Checks

- OS version and kernel check.
- SSH key login check.
- Package install check.
- Read-only mount check.
- ClamAV/YARA scan check.
- API/WebSocket scan check.
- systemd restart check.

### 9.3 Acceptance Criteria Coverage

| Acceptance Area | Covered In |
|---|---|
| Core scanning AC-001 to AC-006 | P2, P3, P7, P8 |
| UI AC-010 to AC-014 | P5, P6, P7, P8 |
| API/network AC-020 to AC-023 | P4, P7, P8 |
| Data/update AC-030 to AC-033 | P2, P4, P8 |
| Security AC-040 to AC-042 | P3, P8 |

---

## 10. Immediate Next Actions

1. Create project skeleton and dependency file.
2. Add config models and default config template.
3. Add SQLite migration/bootstrap module.
4. Add `FileEnumerator` and Quick Scan filter.
5. Add ClamAV adapter and EICAR validation path.
6. Add minimal FastAPI app with `/api/v1/status`.
7. Bring up Radxa OS in parallel if the board is available.

---

## 11. Risks During Implementation

| Risk | Watch For | Response |
|---|---|---|
| 1 GB RAM too tight for `clamd` | OOM, swap pressure, slow scans | Switch default to `clamscan`, reduce archive/file limits |
| microSD write pressure | Frequent progress commits, large logs | Throttle DB writes, use log rotation, avoid clean-file metadata |
| udev complexity | Duplicate events, partitions vs whole disk confusion | Debounce by UUID/device path, only mount supported partitions |
| Display delay | Real UI blocked | Continue simulator-driven integration |
| HAT power draw | Reboots, display flicker | Add external 3.3V regulator and document wiring |

---

## 12. Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-07-09 | - | Initial implementation plan from SRS v1.1, HLD v1.1, and LLD v0.2 |

---

*End of Document*
