#!/usr/bin/env python3
"""Write the standard EICAR test file for threat-path validation."""

from __future__ import annotations

from pathlib import Path

EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def main() -> None:
    target = Path("tests/fixtures/eicar/eicar.com")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(EICAR)
    print(f"Wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
