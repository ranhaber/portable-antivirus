from fastapi import Request
from fastapi.responses import JSONResponse

from portable_av.common.errors import PortableAvError


def portable_av_error_status(exc: PortableAvError) -> int:
    mapping = {
        "no_drive_mounted": 409,
        "scan_already_running": 409,
        "invalid_state_transition": 409,
        "scan_not_found": 404,
        "unauthorized": 401,
        "forbidden": 403,
        "storage_threshold_exceeded": 507,
    }
    return mapping.get(exc.code, 500)


async def portable_av_exception_handler(_: Request, exc: PortableAvError) -> JSONResponse:
    return JSONResponse(
        status_code=portable_av_error_status(exc),
        content={
            "code": exc.code,
            "message": exc.user_message,
            "detail": exc.detail,
        },
    )
