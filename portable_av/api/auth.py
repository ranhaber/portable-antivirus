"""Bearer token authentication for write endpoints."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from portable_av.api.dependencies import AppState, get_app_state

security = HTTPBearer(auto_error=False)


def require_write_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    state: AppState = Depends(get_app_state),
) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    # Token verification is implemented in a later phase.
    if not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    _ = state.config.api.auth_token_hash
