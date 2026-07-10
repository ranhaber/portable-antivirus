from pathlib import Path

from fastapi import APIRouter, Depends, Response, status

from portable_av.api.auth import require_write_auth
from portable_av.api.dependencies import AppState, get_app_state
from portable_av.api.schemas import (
    ProgressResponse,
    StartScanRequest,
    StartScanResponse,
    ThreatActionRequest,
)
from portable_av.common.errors import PortableAvError
from portable_av.common.models import ScanState, ThreatAction

router = APIRouter(tags=["scan"])


def _progress_response(state: AppState) -> ProgressResponse:
    progress = state.scan_controller.get_progress()
    return ProgressResponse(
        scan_id=progress.scan_id,
        state=progress.state,
        stage=progress.stage,
        files_total=progress.files_total,
        files_scanned=progress.files_scanned,
        bytes_scanned=progress.bytes_scanned,
        threats=progress.threats,
        current_file=progress.current_file,
        progress_percent=progress.progress_percent,
    )


@router.post("/scan", response_model=StartScanResponse)
async def start_scan(
    body: StartScanRequest,
    state: AppState = Depends(get_app_state),
    _: None = Depends(require_write_auth),
) -> StartScanResponse:
    scan_root = Path(body.scan_root) if body.scan_root else None
    scan_id = await state.scan_controller.start_scan(
        body.mode,
        requested_by="api",
        scan_root=scan_root,
    )
    return StartScanResponse(scan_id=scan_id, state=ScanState.SCANNING)


@router.delete("/scan", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_scan(
    state: AppState = Depends(get_app_state),
    _: None = Depends(require_write_auth),
) -> Response:
    await state.scan_controller.cancel_scan()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/scan/progress", response_model=ProgressResponse)
def get_progress(state: AppState = Depends(get_app_state)) -> ProgressResponse:
    return _progress_response(state)


@router.post("/scan/threat-action", status_code=status.HTTP_204_NO_CONTENT)
async def threat_action(
    body: ThreatActionRequest,
    state: AppState = Depends(get_app_state),
    _: None = Depends(require_write_auth),
) -> Response:
    await state.scan_controller.handle_threat_action(body.action)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
