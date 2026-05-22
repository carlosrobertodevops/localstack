class AzureError(Exception):
    """Base exception for Azure emulation errors."""

    status_code = 500
    code = "AzureError"

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class AzureUnsupportedOperation(AzureError):
    """Raised when an Azure provider, resource type, or operation is not implemented."""

    status_code = 501
    code = "UnsupportedAzureOperation"


class AzureInvalidRequest(AzureError):
    """Raised when an Azure request is syntactically valid but unsupported or inconsistent."""

    status_code = 400
    code = "InvalidRequest"


class AzureNotFound(AzureError):
    """Raised when an Azure resource cannot be found."""

    status_code = 404
    code = "ResourceNotFound"


class AzureInvalidResourceId(ValueError):
    """Raised when an Azure Resource ID cannot be parsed."""
