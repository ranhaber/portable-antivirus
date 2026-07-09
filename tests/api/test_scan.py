import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from portable_av.api.app import create_app
from portable_av.common.domain import DriveInfo
from portable_av.engine.interfaces import EngineResult


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
    app.state.app_state.paths.data = tmp_path / "data"
    app.state.app_state.paths.reports = tmp_path / "reports"
    app.state.app_state.paths.temp = tmp_path / "tmp"
    app.state.app_state.paths.ensure_runtime_dirs()
    return app


@pytest.fixture
def client(app_bundle) -> TestClient:
    return TestClient(app_bundle)


def test_start_scan_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/scan", json={"mode": "quick"})
    assert response.status_code == 401


@patch("portable_av.engine.scan_controller.ClamAvAdapter.scan_file", new_callable=AsyncMock)
def test_scan_fixture_directory(mock_scan, client: TestClient, app_bundle, tmp_path: Path) -> None:
    mock_scan.return_value = EngineResult(
        engine="clamav",
        clean=True,
        signature=None,
        raw_output="OK",
    )
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "sample.exe").write_bytes(b"MZ")

    response = client.post(
        "/api/v1/scan",
        json={"mode": "quick"},
        headers={"Authorization": "Bearer dev-token"},
    )
    assert response.status_code == 409

    drive = DriveInfo(
        device="/dev/sda1",
        mount_path=fixture,
        label="TEST",
        uuid="TEST-UUID",
        filesystem="vfat",
        size_bytes=1024,
        readonly=True,
    )

    asyncio.run(app_bundle.state.app_state.scan_controller.set_drive(drive))
    response = client.post(
        "/api/v1/scan",
        json={"mode": "quick"},
        headers={"Authorization": "Bearer dev-token"},
    )
    assert response.status_code == 200
    scan_id = response.json()["scan_id"]

    deadline = time.time() + 5
    while time.time() < deadline:
        progress = client.get("/api/v1/scan/progress").json()
        if progress["state"] == "complete":
            break
        time.sleep(0.1)

    record = app_bundle.state.app_state.history_repository.get_scan(scan_id)
    assert record is not None
    assert record["files_scanned"] == 1
