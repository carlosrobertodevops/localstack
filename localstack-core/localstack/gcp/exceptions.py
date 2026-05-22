class GcpError(Exception):
    """Base exception for GCP emulation errors."""

    status_code = 500
    code = "GcpError"

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class GcpUnsupportedOperation(GcpError):
    status_code = 501
    code = "UnsupportedGcpOperation"


class GcpInvalidRequest(GcpError):
    status_code = 400
    code = "InvalidRequest"


class GcpNotFound(GcpError):
    status_code = 404
    code = "ResourceNotFound"


class GcpAlreadyExists(GcpError):
    status_code = 409
    code = "AlreadyExists"


class GcpInvalidResourceName(ValueError):
    """Raised when a GCP resource name cannot be parsed."""
