"""
Shared foundation layer.

This package must not import from api, engine, display, mount, history,
reports, or update. Other packages may depend on common.
"""

from portable_av.common.config import AppConfig
from portable_av.common.config_loader import load_config
from portable_av.common.errors import PortableAvError
from portable_av.common.models import ScanMode, ScanState, ScanStage, ScanStatus

__all__ = [
    "AppConfig",
    "PortableAvError",
    "ScanMode",
    "ScanStage",
    "ScanState",
    "ScanStatus",
    "load_config",
]
