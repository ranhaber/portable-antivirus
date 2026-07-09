import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from portable_av.api.app import create_app
from portable_av.common.domain import DriveInfo


@pytest.fixture
def app_bundle(tmp_path: Path):
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
    app.state.app_state.internal_token = "test-internal-token"
    token_path = app.state.app_state.paths.runtime / "internal.token"
    token_path.write_text("test-internal-token\n", encoding="utf-8")
    return app


@pytest.fixture
def client(app_bundle) -> TestClient:
    return TestClient(app_bundle)


def test_internal_drive_mount_and_remove(client: TestClient, app_bundle) -> None:
    headers = {"X-Internal-Token": "test-internal-token"}
    response = client.post(
        "/api/v1/internal/drive",
        headers=headers,
        json={
            "event": "mounted",
            "device": "/dev/sda1",
            "mount_path": "/mnt/portable-av/TEST-UUID",
            "label": "USB",
            "uuid": "TEST-UUID",
            "filesystem": "vfat",
            "size_bytes": 1024,
            "readonly": True,
        },
    )
    assert response.status_code == 204

    drive = client.get("/api/v1/drive")
    assert drive.status_code == 200
    assert drive.json()["uuid"] == "TEST-UUID"

    remove = client.post(
        "/api/v1/internal/drive",
        headers=headers,
        json={"event": "removed", "device": "/dev/sda1"},
    )
    assert remove.status_code == 204
    assert client.get("/api/v1/drive").status_code == 404


def test_internal_drive_rejects_missing_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/internal/drive",
        json={"event": "removed", "device": "/dev/sda1"},
    )
    assert response.status_code == 401
