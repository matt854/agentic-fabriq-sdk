"""
Authentication and authorization utilities for Agentic Fabric SDK.
"""

from .oauth import (
    api_key_required,
    mtls_required,
    no_auth_required,
    oauth_required,
    ScopeValidator,
    TokenValidator,
)
from .token_cache import TokenManager, VaultClient
from .applications import (
    get_application_client,
    load_application_config,
    save_application_config,
    list_applications,
    delete_application_config,
    ApplicationNotFoundError,
    AuthenticationError,
)

# DPoP helper will be provided from af_sdk.auth.dpop
try:
    from .dpop import create_dpop_proof
except Exception:  # pragma: no cover - optional import if file missing
    create_dpop_proof = None  # type: ignore

__all__ = [
    "oauth_required",
    "api_key_required",
    "mtls_required",
    "no_auth_required",
    "ScopeValidator",
    "TokenValidator",
    "TokenManager",
    "VaultClient",
    "create_dpop_proof",
    "get_application_client",
    "load_application_config",
    "save_application_config",
    "list_applications",
    "delete_application_config",
    "ApplicationNotFoundError",
    "AuthenticationError",
] 