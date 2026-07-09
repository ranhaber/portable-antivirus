from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


def notify_drive_event(url: str, token: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Internal-Token": token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status >= 400:
                logger.warning("Engine notification returned HTTP %s", response.status)
    except urllib.error.URLError as exc:
        logger.warning("Engine notification failed: %s", exc)
