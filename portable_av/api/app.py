from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from portable_av import __version__
from portable_av.api.dependencies import AppState, build_app_state
from portable_av.api.error_handlers import portable_av_exception_handler
from portable_av.api.routes_drive import router as drive_router
from portable_av.api.routes_internal import router as internal_router
from portable_av.api.routes_scan import router as scan_router
from portable_av.api.routes_status import router as status_router
from portable_av.api.websocket import router as websocket_router
from portable_av.common.config_loader import load_config
from portable_av.common.errors import PortableAvError
from portable_av.common.logging import setup_logging
from portable_av.common.paths import AppPaths


def create_app(config_path: Path | None = None) -> FastAPI:
    setup_logging()
    resolved_config_path = config_path or Path(
        os.environ.get("PORTABLE_AV_CONFIG", "config/dev.config.json")
    )
    config = load_config(resolved_config_path)
    paths = AppPaths(
        config_file=resolved_config_path,
        data=Path(os.environ.get("PORTABLE_AV_DATA", "var/lib/portable-av")),
        logs=Path(os.environ.get("PORTABLE_AV_LOGS", "var/log/portable-av")),
        runtime=Path(os.environ.get("PORTABLE_AV_RUNTIME", "var/run/portable-av")),
        temp=Path(os.environ.get("PORTABLE_AV_TEMP", "var/tmp/portable-av")),
    )
    paths.ensure_runtime_dirs()

    app = FastAPI(
        title="Portable Antivirus Appliance",
        version=__version__,
    )
    app.state.app_state = build_app_state(config=config, paths=paths)
    app.add_exception_handler(PortableAvError, portable_av_exception_handler)
    app.include_router(status_router, prefix="/api/v1")
    app.include_router(drive_router, prefix="/api/v1")
    app.include_router(scan_router, prefix="/api/v1")
    app.include_router(internal_router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/api/v1")
    return app


def main() -> None:
    import uvicorn

    config_path = Path(os.environ.get("PORTABLE_AV_CONFIG", "config/dev.config.json"))
    config = load_config(config_path)
    uvicorn.run(
        "portable_av.api.app:create_app",
        factory=True,
        host=config.api.bind_host,
        port=config.api.bind_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
