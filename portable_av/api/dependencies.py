from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request

from portable_av.common.config import AppConfig
from portable_av.common.paths import AppPaths
from portable_av.engine.event_bus import EventBus
from portable_av.engine.scan_controller import ScanController
from portable_av.history.repository import HistoryRepository


@dataclass
class AppState:
    config: AppConfig
    paths: AppPaths
    started_at: datetime
    internal_token: str
    event_bus: EventBus
    scan_controller: ScanController
    history_repository: HistoryRepository


def _ensure_internal_token(runtime_dir: Path) -> str:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    token_path = runtime_dir / "internal.token"
    if token_path.is_file():
        token = token_path.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(32)
    token_path.write_text(token + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    return token


def build_app_state(*, config: AppConfig, paths: AppPaths) -> AppState:
    history_repository = HistoryRepository(paths.history_db)
    history_repository.initialize()
    event_bus = EventBus()
    internal_token = _ensure_internal_token(paths.runtime)
    scan_controller = ScanController(
        config=config,
        paths=paths,
        history_repository=history_repository,
        event_bus=event_bus,
    )
    return AppState(
        config=config,
        paths=paths,
        started_at=datetime.now(timezone.utc),
        internal_token=internal_token,
        event_bus=event_bus,
        scan_controller=scan_controller,
        history_repository=history_repository,
    )


def get_app_state(request: Request) -> AppState:
    return request.app.state.app_state
