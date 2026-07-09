from fastapi import APIRouter, Depends, HTTPException, status

from portable_av.api.dependencies import AppState, get_app_state
from portable_av.api.routes_status import _drive_to_response
from portable_av.api.schemas import DriveInfoResponse

router = APIRouter(tags=["drive"])


@router.get("/drive", response_model=DriveInfoResponse)
def get_drive(state: AppState = Depends(get_app_state)) -> DriveInfoResponse:
    engine_status = state.scan_controller.get_status()
    if engine_status.drive is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No drive mounted.")
    return _drive_to_response(engine_status.drive)
