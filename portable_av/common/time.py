from datetime import UTC, datetime
import secrets


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_scan_id(now: datetime | None = None) -> str:
    """Return YYYYMMDD-HHMMSS-xxxx scan identifiers."""
    stamp = (now or utc_now()).strftime("%Y%m%d-%H%M%S")
    suffix = secrets.token_hex(2)
    return f"{stamp}-{suffix}"
