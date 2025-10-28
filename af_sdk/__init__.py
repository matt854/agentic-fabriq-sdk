"""
Agentic Fabric SDK

Official Python SDK for building connectors and interacting with Agentic Fabric.
"""

from .auth.oauth import oauth_required
from .connectors.base import AgentConnector, ConnectorContext, ToolConnector
from .exceptions import (
    AFError,
    AuthenticationError,
    AuthorizationError,
    ConnectorError,
    NotFoundError,
    ValidationError,
)
from .models.types import (
    ToolInvokeRequest,
    ToolInvokeResult,
)
from .transport.http import HTTPClient
from .fabriq_client import FabriqClient
from .models.audit import AuditEvent
from .auth import (
    get_application_client,
    load_application_config,
    save_application_config,
    list_applications,
    delete_application_config,
    ApplicationNotFoundError,
)

__version__ = "1.0.0"

__all__ = [
    "oauth_required",
    "ToolConnector",
    "AgentConnector",
    "ConnectorContext",
    "AFError",
    "AuthenticationError",
    "AuthorizationError",
    "ConnectorError",
    "NotFoundError",
    "ValidationError",
    "ToolInvokeRequest",
    "ToolInvokeResult",
    "HTTPClient",
    "FabriqClient",
    "AuditEvent",
    # Application auth helpers
    "get_application_client",
    "load_application_config",
    "save_application_config",
    "list_applications",
    "delete_application_config",
    "ApplicationNotFoundError",
] 

# Lazy expose dx submodule under af_sdk.dx
from importlib import import_module as _import_module  # noqa: E402

def __getattr__(name):
    if name == "dx":
        return _import_module("af_sdk.dx")
    raise AttributeError(name)