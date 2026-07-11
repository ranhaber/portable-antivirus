# Agent Notes — Portable Antivirus

Project context for AI agents working on this repository.

## Target Hardware

| Field | Value |
|---|---|
| **Board** | Radxa Zero 3W |
| **OS** | Armbian Ubuntu 24.04 Noble Minimal (CLI), vendor kernel 6.1.115 |
| **Hostname** | `radxazero3` |

## Radxa OS Packages (headless dev)

```bash
sudo apt install -y python3 python3-venv python3-pip clamav clamav-daemon clamdscan ntfs-3g
```

`ntfs-3g` is required for NTFS USB drives (validated 2026-07-10).
`clamdscan` is the daemon client the engine uses in strict `clamd` mode (GATE-004). Configure the daemon with `sudo sh tools/setup_clamd.sh` (tuned for 1 GB RAM). Do not add automatic `clamscan` fallback on the Radxa; it can duplicate ClamAV DB memory and OOM the 1 GB board.

## Dev Board SSH Access

| Field | Value |
|---|---|
| **Host** | `192.168.7.61` |
| **Username** | `radxa03virus` |
| **Password** | Not stored in repository |

```bash
ssh radxa03virus@192.168.7.61
```

## Related Docs

- `SRS.md` — Software Requirements Specification
- `HLD.md` — High-Level Design
