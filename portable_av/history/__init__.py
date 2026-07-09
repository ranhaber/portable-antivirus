"""
SQLite persistence layer.

May depend on: common.
Must not import from api, engine, display, or mount.
"""

from portable_av.history.repository import HistoryRepository

__all__ = ["HistoryRepository"]
