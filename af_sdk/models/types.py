"""
Pydantic models for Agentic Fabric SDK.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Tool(BaseModel):
    """Tool model."""

    id: str
    name: str
    version: str
    description: Optional[str] = None
    protocol: str = "MCP"
    auth_type: str = "OAuth2"
    scopes: List[str] = Field(default_factory=list)
    endpoints: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ToolInvokeRequest(BaseModel):
    """Request model for invoking a tool.

    DX alignment: Gateway expects `parameters` and `context`.
    For backward compatibility, we still accept `args` on input and map it to `parameters`.
    """

    method: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    # Back-compat input alias; not used in output
    args: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None

    # Support pydantic v1 and v2 root validation to map args->parameters
    @classmethod
    def __get_validators__(cls):  # type: ignore[override]
        # Pydantic v1 compatibility hook
        yield cls._pre_root_validator

    @classmethod
    def _pre_root_validator(cls, values):
        # When constructed from dict, map legacy `args` to `parameters` if provided
        if isinstance(values, dict):
            if "parameters" not in values and "args" in values and isinstance(values["args"], dict):
                # Don't mutate original input dict unexpectedly
                new_values = dict(values)
                new_values["parameters"] = new_values.get("args", {}) or {}
                return new_values
        return values


class ToolInvokeResult(BaseModel):
    """Result model for tool invocation.

    DX alignment: Gateway returns `{ result, metadata, logs }`.
    We keep prior fields (`status`, `data`, `headers`) optional for back-compat.
    """

    # Gateway-aligned fields
    result: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    logs: Optional[list[str]] = None

    # Back-compat fields
    status: Optional[str] = None
    data: Optional[Any] = None
    headers: Dict[str, str] = Field(default_factory=dict)


class Secret(BaseModel):
    """Secret model."""

    path: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: int
    created_at: datetime


class SecretMetadata(BaseModel):
    """Secret metadata model."""

    path: str
    version: int
    created_at: datetime
    updated_at: datetime
    versions: List[int] = Field(default_factory=list)


class SecretPutRequest(BaseModel):
    """Request model for creating/updating a secret."""

    path: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TokenExchangeRequest(BaseModel):
    """Request model for token exchange (RFC 8693)."""

    subject_token: str
    actor_token: Optional[str] = None
    scope: Optional[str] = None
    audience: Optional[str] = None


class TokenExchangeResponse(BaseModel):
    """Response model for token exchange."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None


class OAuthToken(BaseModel):
    """OAuth token model."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: datetime
    scopes: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    message: str
    request_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class PaginatedResponse(BaseModel):
    """Paginated response model."""

    items: List[Any]
    total: int
    page: int = 1
    page_size: int = 50
    has_next: bool = False
    has_prev: bool = False


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    timestamp: datetime
    components: Dict[str, str] = Field(default_factory=dict)


class MetricsResponse(BaseModel):
    """Metrics response model."""

    requests_total: int
    requests_per_second: float
    avg_response_time: float
    error_rate: float
    active_connections: int 