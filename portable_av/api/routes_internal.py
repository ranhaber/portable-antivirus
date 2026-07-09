from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from portable_av.api.dependencies import AppState, get_app_state
from portable_av.common.domain import DriveInfo

router = APIRouter(tags=["internal"])


class InternalDriveEvent(BaseModel):
    event: str
    device: str
    mount_path: str | None = None
    label: str | None = None
    uuid: str | None = None
    filesystem: str | None = None
    size_bytes: int | None = None
    readonly: bool = True


def _require_localhost(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Localhost only.")


def _require_internal_token(
    request: Request,
    state: AppState = Depends(get_app_state),
    token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    _require_localhost(request)
    if not token or token != state.internal_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token.")


@router.post("/internal/drive", status_code=status.HTTP_204_NO_CONTENT)
async def internal_drive_event(
    body: InternalDriveEvent,
    _: None = Depends(_require_internal_token),
    state: AppState = Depends(get_app_state),
) -> None:
    if body.event == "removed":
        await state.scan_controller.set_drive(None)
        await state.event_bus.publish("drive_removed", {"device": body.device})
        return

    if body.event != "mounted" or not body.mount_path:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid mount event.")

    drive = DriveInfo(
        device=body.device,
        mount_path=Path(body.mount_path),
        label=body.label,
        uuid=body.uuid,
        filesystem=body.filesystem or "unknown",
        size_bytes=body.size_bytes,
        readonly=body.readonly,
    )
    await state.scan_controller.set_drive(drive)
    await state.event_bus.publish(
        "drive_mounted",
        {
            "device": drive.device,
            "mount_path": str(drive.mount_path),
            "label": drive.label,
            "uuid": drive.uuid,
            "filesystem": drive.filesystem,
            "size_bytes": drive.size_bytes,
            "readonly": drive.readonly,
        },
    )
