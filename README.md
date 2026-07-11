# Portable Antivirus Appliance

Standalone malware scanning appliance for removable media, targeting a Radxa Zero 3W running Armbian Ubuntu 24.04 Noble Minimal.

The appliance is designed to scan USB flash drives, low-power portable SSDs, SD cards, and microSD cards without requiring a host PC. All external media is mounted read-only, then scanned with ClamAV and YARA. Results are shown locally on a small multi-display UI and exposed through a headless API for web or companion clients.

## Status

Headless prototype validated on Radxa Zero 3W (2026-07-10):

- Real NTFS USB mounted read-only and reported via API
- Quick Scan completed through ClamAV/YARA pipeline (3 files, 0 threats)
- WebSocket events and display simulator working against live engine
- USB auto-mount validated end-to-end: physical unplug/re-plug re-enumerated as `/dev/sdb1` and auto-mounted read-only via udev/systemd
- EICAR threat-path validated: `Eicar-Test-Signature` → `threat_prompt` → stop → `threats=1`

- ClamAV mode resolved to strict `clamd` + `clamdscan --fdpass`: warm scans ~0.3 s vs ~94 s for `clamscan`; no automatic `clamscan` fallback on the 1 GB board

Remaining before v1 prototype: engine systemd service for boot-time operation, large-file/archive limit benchmarking, display HAT integration.

## Target Platform

- Board: Radxa Zero 3W
- OS: Armbian Ubuntu 24.04 Noble Minimal, vendor kernel 6.1.115
- Runtime: Python 3.11+
- Scan engines: ClamAV 1.x and YARA 4.x
- Display: Waveshare Zero LCD HAT (A) / Triple IPS LCD HAT
- Storage: 32 GB microSD for OS, databases, reports, and history

## Core Goals

- Detect removable media insertion.
- Mount external filesystems read-only.
- Provide Quick Scan and Full Scan modes.
- Scan files with ClamAV and YARA.
- Generate TXT and HTML reports.
- Store scan history in SQLite.
- Support local operator feedback through three displays and two buttons.
- Expose REST and WebSocket interfaces for administration, monitoring, and future clients.

## Repository Contents

- `SRS.md` - software requirements specification.
- `HLD.md` - high-level design and architecture.
- `LLD.md` - low-level design, package layout, service contracts, and implementation details.
- `IMPLEMENTATION_PLAN.md` - phased implementation plan and headless sprint schedule.
- `portable_av/` - modular Python application package.
- `config/` - development and example configuration files.
- `tests/` - module-aligned unit and API tests.
- `tools/` - bring-up helpers and display simulator.
- `deploy/` - udev rules, systemd units, env-file wrapper, dev install script.
- `bind_sd.ps1` - Windows helper for binding the SD card into WSL workflows.
- `mount_sd.ps1` - Windows helper for mounting SD media.
- `sd_check.sh` - Linux shell helper for checking SD/media state.
- `ssh_test.sh` - SSH connectivity helper for the dev board.
- `AGENTS.md` - local agent context for this repository.

## Application Modules

The Python package is split by responsibility:

| Module | Role |
|---|---|
| `portable_av.common` | Shared config, models, errors, paths, time helpers |
| `portable_av.api` | FastAPI REST/WebSocket boundary |
| `portable_av.engine` | Scan controller and malware engine adapters |
| `portable_av.history` | SQLite persistence |
| `portable_av.mount` | Read-only mount helper and engine notification |
| `portable_av.reports` | TXT/HTML report generation |
| `portable_av.display` | Local LCD/button service |
| `portable_av.update` | ClamAV and YARA update helpers |

Import rules:

- `common` does not import feature packages.
- `engine` does not import `api` or `display`.
- `display` talks to the engine only through REST/WebSocket.
- `mount` notifies the engine over localhost HTTP and does not write SQLite directly.

## Development

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
python -m portable_av.api.app
```

### Linux (Radxa / Armbian)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip clamav clamav-daemon clamdscan ntfs-3g
git clone https://github.com/ranhaber/portable-antivirus.git
cd portable-antivirus
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
PORTABLE_AV_CONFIG=config/dev.config.json python -m portable_av.api.app
```

ClamAV daemon (recommended engine mode, tuned for 1 GB RAM):

```bash
sudo sh tools/setup_clamd.sh          # installs clamdscan, tunes + starts clamd
sh tools/benchmark_clamav.sh          # optional: clamscan vs clamdscan comparison
```

The prototype keeps the full official ClamAV DB by default (`main.cvd`, `daily.cvd`, `bytecode.cvd`). In `clamd` mode, `clamdscan` is required; the engine does not automatically fall back to `clamscan` because that can duplicate DB memory and OOM the 1 GB board.

USB auto-mount (development checkout):

```bash
sudo sh deploy/install-dev.sh
```

Manual mount test:

```bash
sudo PORTABLE_AV_RUNTIME=$PWD/var/run/portable-av .venv/bin/python -m portable_av.mount.mount_manager --device /dev/sda1
```

Start Quick Scan (API must be running):

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

Headless fixture scan:

```bash
source .venv/bin/activate
python -m portable_av.engine.cli tests/fixtures/clean --mode full --auto-continue
```

Status endpoint for the skeleton:

```text
GET http://127.0.0.1:8080/api/v1/status
GET http://127.0.0.1:8080/api/v1/drive
GET http://127.0.0.1:8080/api/v1/scan/progress
POST http://127.0.0.1:8080/api/v1/scan  (body: {"mode":"quick"|"full"}, Bearer auth)
WS  ws://127.0.0.1:8080/api/v1/scan/events
```

## Security Notes

- Scanned media must remain read-only in v1. The appliance must not modify, quarantine, or delete files on source media.
- Do not commit provisioning files, Wi-Fi passwords, board passwords, private keys, tokens, or generated secrets.
- The file `not_logged_in_yet` is intentionally ignored because it may contain first-run credentials.

## Documentation

Start with the documents in this order:

1. `SRS.md` for product scope and requirements.
2. `HLD.md` for architecture and major design decisions.
3. `LLD.md` for concrete module boundaries, services, data types, and implementation notes.
