from __future__ import annotations


def progress_percent(files_scanned: int, files_total: int | None) -> float | None:
    if files_total is None or files_total <= 0:
        return None
    return round(min(files_scanned / files_total, 1.0) * 100.0, 1)
