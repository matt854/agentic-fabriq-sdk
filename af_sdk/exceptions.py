"""
Exception classes for the Agentic Fabric SDK.
"""

from typing import Any, Dict, Optional


class AFError(Exception):
    """Base exception for all Agentic Fabric errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "SERVER_ERROR",
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.request_id = request_id
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


class AuthenticationError(AFError):
    """Authentication failed - missing or invalid JWT or mTLS cert."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_FAILED", **kwargs)


class AuthorizationError(AFError):
    """Authorization failed - OPA policy denied or scope mismatch."""

    def __init__(self, message: str = "Authorization denied", **kwargs):
        super().__init__(message, error_code="FORBIDDEN", **kwargs)


class NotFoundError(AFError):
    """Resource or endpoint not found."""

    def __init__(self, message: str = "Resource not found", **kwargs):
        super().__init__(message, error_code="NOT_FOUND", **kwargs)


class ValidationError(AFError):
    """Request validation failed."""

    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)


class ConflictError(AFError):
    """Resource conflict - duplicate ID or version clash."""

    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(message, error_code="CONFLICT", **kwargs)


class RateLimitError(AFError):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(message, error_code="RATE_LIMITED", **kwargs)


class UpstreamError(AFError):
    """Error from upstream service."""

    def __init__(self, message: str = "Upstream service error", **kwargs):
        super().__init__(message, error_code="UPSTREAM_ERROR", **kwargs)


class ServiceUnavailableError(AFError):
    """Service temporarily unavailable."""

    def __init__(self, message: str = "Service unavailable", **kwargs):
        super().__init__(message, error_code="SERVICE_UNAVAILABLE", **kwargs)


class ConnectorError(AFError):
    """Error in connector implementation."""

    def __init__(self, message: str = "Connector error", **kwargs):
        super().__init__(message, error_code="CONNECTOR_ERROR", **kwargs)


class TokenRefreshError(AFError):
    """Failed to refresh OAuth token."""

    def __init__(self, message: str = "Token refresh failed", **kwargs):
        super().__init__(message, error_code="TOKEN_REFRESH_ERROR", **kwargs)


class VaultError(AFError):
    """Error accessing vault/secrets."""

    def __init__(self, message: str = "Vault error", **kwargs):
        super().__init__(message, error_code="VAULT_ERROR", **kwargs)


class EventError(AFError):
    """Error in event processing."""

    def __init__(self, message: str = "Event error", **kwargs):
        super().__init__(message, error_code="EVENT_ERROR", **kwargs)


# Mapping from error codes to exception classes
ERROR_CODE_TO_EXCEPTION = {
    "AUTHENTICATION_FAILED": AuthenticationError,
    "FORBIDDEN": AuthorizationError,
    "NOT_FOUND": NotFoundError,
    "VALIDATION_ERROR": ValidationError,
    "CONFLICT": ConflictError,
    "RATE_LIMITED": RateLimitError,
    "UPSTREAM_ERROR": UpstreamError,
    "SERVICE_UNAVAILABLE": ServiceUnavailableError,
    "CONNECTOR_ERROR": ConnectorError,
    "TOKEN_REFRESH_ERROR": TokenRefreshError,
    "VAULT_ERROR": VaultError,
}


def create_exception_from_response(response_data: Dict[str, Any]) -> AFError:
    """Create an exception from an API error response."""
    error_code = response_data.get("error", "SERVER_ERROR")
    message = response_data.get("message", "Unknown error")
    request_id = response_data.get("request_id")
    details = response_data.get("details", {})

    exception_class = ERROR_CODE_TO_EXCEPTION.get(error_code, AFError)
    return exception_class(
        message=message,
        request_id=request_id,
        details=details,
    ) 