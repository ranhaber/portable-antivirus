import logging
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
