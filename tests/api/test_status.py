import json
from pathlib import Path

from fastapi.testclient import TestClient

from portable_av.api.app import create_app


def test_status_endpoint_returns_idle_state(tmp_path: Path) -> None:
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
    client = TestClient(app)

    response = client.get("/api/v1/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "idle"
    assert payload["active_scan_id"] is None
    assert payload["drive"] is None
