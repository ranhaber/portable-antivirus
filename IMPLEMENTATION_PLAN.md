# Implementation Plan

## Portable Antivirus Appliance

| Field | Value |
|---|---|
| **Document ID** | PLAN-PAV-001 |
| **Version** | 0.4 |
| **Date** | 2026-07-10 |
| **Status** | In progress — Day 3 validated on Radxa; deploy install and systemd mount validated |
| **Source Requirements** | `SRS.md` v1.1 |
| **Source Architecture** | `HLD.md` v1.1 |
| **Source Design** | `LLD.md` v0.4 |
| **Target Hardware** | Radxa Zero 3W, 1 GB LPDDR4, 32 GB microSD, Waveshare Zero LCD HAT (A) |
| **Target OS** | Armbian Ubuntu 24.04 Noble Minimal (CLI), vendor kernel 6.1.115 |
| **Repository** | https://github.com/ranhaber/portable-antivirus.git |

---

## 1. Purpose

This plan converts the approved SRS, HLD, and LLD into an ordered implementation path. It starts with the work that can be completed before the display HAT arrives, then adds hardware bring-up, display integration, and end-to-end appliance validation.

The display HAT is expected in approximately 3 days. Until then, implementation focuses on the headless foundation: OS bring-up, scan engine, read-only mount flow, persistence, reports, REST API, WebSocket events, and a simulated display client.

---

## 2. Current Progress Snapshot

| Phase / Day | Status | Evidence |
|---|---|---|
| P0 Project skeleton | **Done** | `portable_av/` package, config, tests, `pyproject.toml` |
| P1 Radxa OS foundation | **Done** | Radxa clones repo, venv, `pytest` 7/7 pass, API starts |
| Day 1 scaffolding | **Done** | Modular package layout, `/api/v1/status`, SQLite bootstrap |
| Day 2 headless scan core | **Done** | Enumerator, ClamAV/YARA adapters, scan controller, reports, CLI |
| Day 3 mount/API/events | **Mostly done** | Real USB mount, scan, WebSocket validated on Radxa |
| P3 read-only mount flow | **Mostly done** | Manual mount, removal wrapper, and systemd service validated; physical re-plug test pending |
| P4 REST API and WebSocket | **Mostly done** | Real Quick Scan + live events on Radxa |
| P5 display simulator | **Done (headless)** | `tools/display_simulator.py` validated against live engine |
| P6 display HAT bring-up | **Blocked** | Waiting for HAT hardware (~3 days) |

**Radxa validated (2026-07-10):**

- `git clone https://github.com/ranhaber/portable-antivirus.git`
- `pip install -r requirements-dev.txt`
- `pytest` → 7 passed
- `python -m portable_av.api.app` → Uvicorn on `http://127.0.0.1:8080`
- NTFS USB (`NirBackups`, `/dev/sda1`) mounted read-only at `/mnt/portable-av/DCF8EB45F8EB1D10` (requires `ntfs-3g`)
- `POST /api/v1/internal/drive` notified engine; `GET /api/v1/drive` and `GET /api/v1/status` show real drive
- `POST /api/v1/scan` with `{"mode":"quick"}` completed: 3 files, 67,930,968 bytes, 0 threats
- WebSocket emitted `scan_started`, stage changes, `scan_progress`, `scan_completed`
- Display simulator showed drive label and live scan progress

**Resolved deploy issue:** udev/systemd auto-mount initially failed with `203/EXEC` because the old unit hardcoded `/opt/portable-av/venv/`. The fix is installed on Radxa via `deploy/install-dev.sh`; `portable-av-mount@sda1.service` now runs `/usr/local/bin/portable-av-mount`, mounts NTFS read-only, and notifies the engine. Physical unplug/re-plug validation remains.

---

## 3. Planning Assumptions

- The fixed target board is Radxa Zero 3W with 1 GB RAM and 32 GB microSD.
- The OS baseline is Armbian Ubuntu 24.04 Noble Minimal (CLI), vendor kernel 6.1.115.
- v1 scan modes are Quick Scan and Full Scan only.
- v1 engines are ClamAV and YARA.
- v1 archive handling uses ClamAV built-in archive scanning only.
- All removable media is mounted read-only.
- Source media is never quarantined, deleted, or modified.
- Display-specific work can use a simulator until the HAT arrives.
- `clamd` is the default design target, with `clamscan` fallback preserved until Radxa benchmarks are complete.
- Radxa pulls code from GitHub public repo, same workflow as other Radxa projects.

---

## 4. Open Decisions and Gates

No open decision blocks Day 3 work. The items below are planned validation gates.

| Gate | Decision | Current Default | Resolution Point |
|---|---|---|---|
| GATE-001 | Display pin map and SPI assignment | Provisional HLD mapping | Display HAT bring-up |
| GATE-002 | Python SPI/GPIO library | `spidev` plus Radxa-compatible GPIO library TBD | Display HAT bring-up |
| GATE-003 | HAT 3.3V power sufficiency | Board 3.3V rail assumed sufficient | Display HAT power test |
| GATE-004 | ClamAV mode | `clamd` preferred, `clamscan` fallback | Headless scan benchmark on Radxa |
| GATE-005 | Progress percentage strategy | Streaming enumeration; optional pre-count | Real-media scan UX benchmark |
| GATE-006 | Threat meter segment count | 12 segments | Display visual review |

If a gate fails, update `LLD.md` §19.1 and the affected configuration defaults before continuing dependent work.

---

## 5. Phase Overview

| Phase | Name | Status | Primary Output |
|---|---|---|---|
| P0 | Project Skeleton and Dev Tooling | Done | Python package, config, install layout |
| P1 | Target OS and Board Foundation | Done | Radxa boots, SSH works, git clone, venv |
| P2 | Headless Scan Core | Done | Scan controller, ClamAV/YARA, reports, history |
| P3 | Read-Only Mount Flow | Mostly done | Manual mount, removal wrapper, and systemd service validated |
| P4 | REST API and WebSocket | Mostly done | Real Quick Scan and live events on Radxa |
| P5 | Display Simulator | Done (headless) | Terminal client validated against live engine |
| P6 | Display HAT Bring-Up | Blocked | Validated SPI/GPIO/power/pin map |
| P7 | Integrated Appliance Loop | Pending | Button-driven end-to-end scanner |
| P8 | Hardening and Acceptance | Pending | v1 prototype acceptance pass |

---

## 6. Three-Day Headless Sprint

### Day 1: OS, Skeleton, and Local Scaffolding — **DONE**

Goal: make the project runnable on development machine and target board.

Completed:

- Radxa reachable over SSH; Python 3, venv, pip, ClamAV installed.
- Modular `portable_av/` package from `LLD.md` §4.
- Config templates under `config/`.
- SQLite migration/bootstrap module.
- FastAPI app with `GET /api/v1/status`.
- GitHub repo published; Radxa clones successfully.

Exit checks:

- [x] `python -m compileall portable_av` passes
- [x] Config validation accepts default config
- [x] Radxa runs `pytest` and starts API

### Day 2: Headless Scan Engine — **DONE**

Goal: scan files without display hardware.

Completed:

- Core enums, dataclasses, and Pydantic models.
- `FileEnumerator` with Quick Scan extension filter.
- `ClamAvAdapter` and `YaraAdapter`.
- `HistoryRepository` CRUD for scans, detections, and events.
- `ScanController` state machine with cancel and threat prompt.
- `ReportWriter` for TXT and HTML.
- Scan API routes: `POST/DELETE /scan`, `GET /scan/progress`, `POST /scan/threat-action`.
- Headless CLI: `python -m portable_av.engine.cli`.

Exit checks:

- [x] Clean fixture scans complete and write reports
- [x] Mocked/API scan path records history
- [x] Cancel path implemented
- [x] Live Quick Scan on Radxa with real ClamAV (3 files, 0 threats, 2026-07-10)
- [ ] Live EICAR detection on Radxa (optional threat-path validation)

### Day 3: Mount, API, Events, and Simulator — **MOSTLY DONE**

Goal: prove the appliance behavior headlessly.

Tasks:

- [x] Implement mount device inspection using `lsblk`/`blkid`
- [x] Implement read-only mount helper and unmount flow
- [x] Draft `udev` rule and `portable-av-mount@.service` under `deploy/`
- [x] Implement internal drive notification endpoint (`POST /api/v1/internal/drive`)
- [x] Implement `GET /api/v1/drive`
- [x] Implement in-process `EventBus`
- [x] Implement WebSocket event stream (`WS /api/v1/scan/events`)
- [x] Implement display simulator (`tools/display_simulator.py`)
- [x] Validate manual USB read-only mount on Radxa (NTFS via `ntfs-3g`)
- [x] Validate WebSocket live events during a real scan on Radxa
- [x] Validate simulator against running engine
- [x] Install updated deploy assets (`deploy/install-dev.sh`) on Radxa
- [x] Validate `portable-av-mount@sda1.service` through systemd (`status=0/SUCCESS`)
- [x] Validate removal wrapper updates API state to idle
- [ ] Validate physical unplug/re-plug udev trigger

Deliverables:

- USB flash drive mounts read-only via mount helper.
- API can start/cancel Quick Scan.
- WebSocket emits progress and threat events.
- Simulator shows scan state, progress, and threat prompt.

Exit checks:

- [x] `mount` shows `ro,nosuid,nodev,noexec` for external media (manual mount validated)
- [x] `POST /api/v1/scan` starts a scan (unit tested)
- [x] `DELETE /api/v1/scan` cancels scan (implemented)
- [x] WebSocket receives `drive_mounted` (unit tested)
- [x] WebSocket receives `scan_started`, `scan_progress`, `scan_completed` on Radxa
- [ ] WebSocket receives `threat_detected` on Radxa (EICAR or test fixture)
- [ ] TXT/HTML reports downloadable through API

---

## 7. Display Arrival Plan

### Day 4: Display HAT Bring-Up — **BLOCKED (hardware)**

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

---

## 8. Remaining Implementation Phases

### P3: Read-Only Mount Flow — In progress

Done when:

- FAT32, exFAT, NTFS, and ext volumes mount read-only on Radxa.
- Unsupported filesystems produce clear errors.
- Media removal is reported without crashing the engine.

### P4: REST API and WebSocket — In progress

Done when:

- API can run the headless scan prototype on Radxa.
- WebSocket clients receive live scan events during real scans.
- Write operations require auth.

### P5: Display Simulator

Done when:

- End-to-end scan can be observed without real display hardware.
- UI state transitions are visible and match SRS.

### P6–P8

Unchanged from original plan. See prior phase descriptions in git history if needed.

---

## 9. Radxa Development Workflow

Clone or update on the board:

```bash
cd ~
git clone https://github.com/ranhaber/portable-antivirus.git
# or, for updates:
cd ~/portable-antivirus && git pull

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
PORTABLE_AV_CONFIG=config/dev.config.json python -m portable_av.api.app
```

Install OS packages (NTFS support required for many USB drives):

```bash
sudo apt install -y ntfs-3g
```

Deploy mount integration for a home checkout:

```bash
cd ~/portable-antivirus
git pull
sudo sh deploy/install-dev.sh
```

This installs `/usr/local/bin/portable-av-mount`, writes `/etc/portable-av/portable-av.env`, and reloads udev/systemd. Unplug and re-plug USB to test auto-mount.

Manual mount test (bypasses udev):

```bash
sudo PORTABLE_AV_RUNTIME=$PWD/var/run/portable-av .venv/bin/python -m portable_av.mount.mount_manager --device /dev/sda1
```

Start scan (separate terminal, API must be running):

```bash
curl -s -X POST http://127.0.0.1:8080/api/v1/scan \
  -H "Authorization: Bearer dev" \
  -H "Content-Type: application/json" \
  -d '{"mode": "quick"}' | python -m json.tool
```

Display simulator (separate terminal):

```bash
source .venv/bin/activate
python tools/display_simulator.py
```

---

## 10. Immediate Next Actions

1. Unplug/re-plug USB and verify udev auto-mount + `GET /api/v1/drive` without manual or `systemctl restart` command.
2. Optional: EICAR threat-path validation (`threat_detected` WebSocket event).
3. Benchmark `clamd` vs `clamscan` on Radxa (GATE-004).
4. Wire engine as systemd service for boot-time operation.
5. Display HAT bring-up when hardware arrives (Day 4).

---

## 11. Risks During Implementation

| Risk | Watch For | Response |
|---|---|---|
| 1 GB RAM too tight for `clamd` | OOM, swap pressure, slow scans | Switch default to `clamscan`, reduce archive/file limits |
| microSD write pressure | Frequent progress commits, large logs | Throttle DB writes, use log rotation, avoid clean-file metadata |
| udev complexity | Duplicate events, partitions vs whole disk confusion | Debounce by UUID/device path, only mount supported partitions |
| Display delay | Real UI blocked | Continue simulator-driven integration |
| HAT power draw | Reboots, display flicker | Add external 3.3V regulator and document wiring |
| Private repo clone issues | GitHub password prompt on Radxa | Keep repo public like other Radxa projects |

---

## 12. Document History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-07-09 | Initial implementation plan from SRS v1.1, HLD v1.1, and LLD v0.2 |
| 0.2 | 2026-07-10 | Marked Day 1–2 done, Radxa git validation, Day 3 scope and progress, deploy workflow |
| 0.3 | 2026-07-10 | Day 3 Radxa validation: real NTFS mount, Quick Scan, WebSocket, simulator; deploy wrapper fix |
| 0.4 | 2026-07-10 | Installed deploy fix on Radxa; validated systemd mount service and removal wrapper |

---

*End of Document*
