class PortableAvError(Exception):
    code: str = "internal_error"
    user_message: str = "An internal error occurred."
    detail: str | None = None

    def __init__(
        self,
        *,
        user_message: str | None = None,
        detail: str | None = None,
    ) -> None:
        if user_message is not None:
            self.user_message = user_message
        self.detail = detail
        super().__init__(self.user_message)


class RecoverableError(PortableAvError):
    pass


class FatalScanError(PortableAvError):
    pass


class NoDriveMountedError(PortableAvError):
    code = "no_drive_mounted"
    user_message = "No removable drive is mounted."


class ScanAlreadyRunningError(PortableAvError):
    code = "scan_already_running"
    user_message = "A scan is already in progress."


class InvalidStateTransitionError(PortableAvError):
    code = "invalid_state_transition"
    user_message = "The requested action is not valid in the current state."


class ScanNotFoundError(PortableAvError):
    code = "scan_not_found"
    user_message = "Scan not found."


class UnauthorizedError(PortableAvError):
    code = "unauthorized"
    user_message = "Authentication required."


class ForbiddenError(PortableAvError):
    code = "forbidden"
    user_message = "You do not have permission to perform this action."


class StorageThresholdExceededError(PortableAvError):
    code = "storage_threshold_exceeded"
    user_message = "Internal storage is too full to start a new scan."
