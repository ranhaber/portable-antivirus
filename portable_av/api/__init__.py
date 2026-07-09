"""
HTTP and WebSocket boundary.

May depend on: common, engine, history, mount, update.
Must not be imported by engine, display, or mount.
"""

from portable_av.api.app import create_app

__all__ = ["create_app"]
