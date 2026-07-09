"""
Scan engine core.

May depend on: common, history, reports.
Must not import from api or display.
"""

from portable_av.engine.scan_controller import ScanController

__all__ = ["ScanController"]
