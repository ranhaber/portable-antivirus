from fastapi import APIRouter, Depends

from portable_av.api.dependencies import AppState, get_app_state
from portable_av.api.schemas import DriveInfoResponse, StatusResponse

router = APIRouter(tags=["status"])


def _drive_to_response(drive) -> DriveInfoResponse | None:
    if drive is None:
        return None
    return DriveInfoResponse(
        device=drive.device,
        mount_path=str(drive.mount_path),
        label=drive.label,
        uuid=drive.uuid,
        filesystem=drive.filesystem,
        size_bytes=drive.size_bytes,
        readonly=drive.readonly,
    )


@router.get("/status", response_model=StatusResponse)
def get_status(state: AppState = Depends(get_app_state)) -> StatusResponse:
    engine_status = state.scan_controller.get_status()
    uptime_sec = int((engine_status.now - state.started_at).total_seconds())
    return StatusResponse(
        state=engine_status.state,
        active_scan_id=engine_status.active_scan_id,
        drive=_drive_to_response(engine_status.drive),
        version=__import__("portable_av").__version__,
        uptime_sec=max(uptime_sec, 0),
    )
