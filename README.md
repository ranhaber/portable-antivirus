# Portable Antivirus Appliance

Standalone malware scanning appliance for removable media, targeting a Radxa Zero 3W running Armbian Ubuntu 24.04 Noble Minimal.

The appliance is designed to scan USB flash drives, low-power portable SSDs, SD cards, and microSD cards without requiring a host PC. All external media is mounted read-only, then scanned with ClamAV and YARA. Results are shown locally on a small multi-display UI and exposed through a headless API for web or companion clients.

## Status

Design baseline and provisioning scripts are in place. Prototype hardware validation and implementation are still pending.

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
sudo apt install -y python3 python3-venv python3-pip clamav clamav-daemon
git clone <repo-url> portable-antivirus
cd portable-antivirus
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
PORTABLE_AV_CONFIG=config/dev.config.json python -m portable_av.api.app
```

Headless fixture scan:

```bash
source .venv/bin/activate
python -m portable_av.engine.cli tests/fixtures/clean --mode full --auto-continue
```

Status endpoint for the skeleton:

```text
GET http://127.0.0.1:8080/api/v1/status
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
