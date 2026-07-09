import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient

from portable_av.api.app import create_app


def test_websocket_receives_drive_mounted(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "api": {
                    "bind_host": "127.0.0.1",
                    "bind_port": 8080,
                    "auth_token_hash": "test",
                    "allow_unauthenticated_read": True,
                },
            }
        ),
        encoding="utf-8",
    )
    app = create_app(config_path)
    app.state.app_state.paths.runtime = tmp_path / "run"
    app.state.app_state.paths.data = tmp_path / "data"
    app.state.app_state.paths.reports = tmp_path / "reports"
    app.state.app_state.paths.temp = tmp_path / "tmp"
    app.state.app_state.paths.ensure_runtime_dirs()
    client = TestClient(app)

    with client.websocket_connect("/api/v1/scan/events") as websocket:
        asyncio.run(
            app.state.app_state.event_bus.publish(
                "drive_mounted",
                {"device": "/dev/sda1", "label": "USB"},
            )
        )
        message = websocket.receive_json()
        assert message["type"] == "drive_mounted"
        assert message["payload"]["label"] == "USB"
