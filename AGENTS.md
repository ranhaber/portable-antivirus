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
sudo apt install -y python3 python3-venv python3-pip clamav clamav-daemon ntfs-3g
```

`ntfs-3g` is required for NTFS USB drives (validated 2026-07-10).

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
