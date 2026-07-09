from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Request

from portable_av.common.config import AppConfig
from portable_av.common.models import ScanState
from portable_av.common.paths import AppPaths
from portable_av.engine.scan_controller import ScanController
from portable_av.history.repository import HistoryRepository


@dataclass
class AppState:
    config: AppConfig
    paths: AppPaths
    started_at: datetime
    scan_controller: ScanController
    history_repository: HistoryRepository


def build_app_state(*, config: AppConfig, paths: AppPaths) -> AppState:
    history_repository = HistoryRepository(paths.history_db)
    history_repository.initialize()
    scan_controller = ScanController(
        config=config,
        paths=paths,
        history_repository=history_repository,
    )
    return AppState(
        config=config,
        paths=paths,
        started_at=datetime.now(timezone.utc),
        scan_controller=scan_controller,
        history_repository=history_repository,
    )


def get_app_state(request: Request) -> AppState:
    return request.app.state.app_state
