"""
OAuth authentication decorator and helpers.
"""

import time
from functools import wraps
from typing import Any, Awaitable, Callable, List, Optional

from ..exceptions import AuthenticationError, TokenRefreshError


def oauth_required(*, scopes: List[str], refresh_if_expired: bool = True):
    """
    Decorator that injects a valid OAuth2 Bearer token for the current user.

    Automatically:
    1. Pulls access token from TokenManager (refreshes if expired)
    2. Populates `Authorization` header
    3. Enforces that requested scopes ⊆ granted scopes

    Args:
        scopes: List of required OAuth scopes
        refresh_if_expired: Whether to attempt token refresh if expired

    Raises:
        AuthenticationError: If token is invalid or missing
        TokenRefreshError: If token refresh fails
    """

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(fn)
        async def wrapper(self, *args, **kwargs):
            ctx = getattr(self, "ctx", None)
            if not ctx:
                raise AuthenticationError("Connector context not available")

            tool_id = getattr(self, "TOOL_ID", None)
            if not tool_id:
                raise AuthenticationError("TOOL_ID not set in connector")

            try:
                # Get OAuth token from token manager
                token = await ctx.token_manager.get_oauth_token(
                    tool_id=tool_id,
                    user_id=ctx.user_id,
                    scopes=scopes,
                    refresh_if_expired=refresh_if_expired,
                )

                # Log token info (first 20 chars for debugging)
                ctx.logger.info(f"OAuth decorator injecting token for {tool_id}: {token[:20]}...")

                # Inject Authorization header
                headers = kwargs.setdefault("headers", {})
                headers.setdefault("Authorization", f"Bearer {token}")

                # Log the request (without token)
                ctx.logger.info(
                    f"Making OAuth request to {tool_id}",
                    extra={"scopes": scopes, "user_id": ctx.user_id},
                )

                return await fn(self, *args, **kwargs)

            except Exception as e:
                ctx.logger.error(f"OAuth authentication failed: {e}")
                if isinstance(e, (AuthenticationError, TokenRefreshError)):
                    raise
                raise AuthenticationError(f"OAuth authentication failed: {e}")

        return wrapper

    return decorator


def api_key_required(*, key_name: str = "api_key", header_name: str = "X-API-Key"):
    """
    Decorator that injects an API key for the current user.

    Args:
        key_name: Name of the API key in the vault
        header_name: HTTP header name for the API key

    Raises:
        AuthenticationError: If API key is missing or invalid
    """

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(fn)
        async def wrapper(self, *args, **kwargs):
            ctx = getattr(self, "ctx", None)
            if not ctx:
                raise AuthenticationError("Connector context not available")

            tool_id = getattr(self, "TOOL_ID", None)
            if not tool_id:
                raise AuthenticationError("TOOL_ID not set in connector")

            try:
                # Get API key from vault
                secret_path = f"af/{ctx.tenant_id}/{ctx.user_id}/api_keys/{tool_id}/{key_name}"
                secret = await ctx.token_manager.vault_client.read_secret(secret_path)
                
                if not secret or "value" not in secret:
                    raise AuthenticationError(f"API key not found: {key_name}")

                api_key = secret["value"]

                # Inject API key header
                headers = kwargs.setdefault("headers", {})
                headers.setdefault(header_name, api_key)

                # Log the request
                ctx.logger.info(
                    f"Making API key request to {tool_id}",
                    extra={"key_name": key_name, "user_id": ctx.user_id},
                )

                return await fn(self, *args, **kwargs)

            except Exception as e:
                ctx.logger.error(f"API key authentication failed: {e}")
                if isinstance(e, AuthenticationError):
                    raise
                raise AuthenticationError(f"API key authentication failed: {e}")

        return wrapper

    return decorator


def mtls_required(*, cert_path: Optional[str] = None, key_path: Optional[str] = None):
    """
    Decorator that configures mutual TLS authentication.

    Args:
        cert_path: Path to client certificate (optional, uses default if not provided)
        key_path: Path to client private key (optional, uses default if not provided)

    Raises:
        AuthenticationError: If mTLS configuration fails
    """

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(fn)
        async def wrapper(self, *args, **kwargs):
            ctx = getattr(self, "ctx", None)
            if not ctx:
                raise AuthenticationError("Connector context not available")

            try:
                # Configure mTLS for the HTTP client
                # This would typically be done at the session level
                # For now, we'll add it to the kwargs
                cert_config = (cert_path, key_path) if cert_path and key_path else None
                kwargs.setdefault("cert", cert_config)

                ctx.logger.info(
                    "Making mTLS request",
                    extra={"cert_path": cert_path, "user_id": ctx.user_id},
                )

                return await fn(self, *args, **kwargs)

            except Exception as e:
                ctx.logger.error(f"mTLS authentication failed: {e}")
                raise AuthenticationError(f"mTLS authentication failed: {e}")

        return wrapper

    return decorator


def no_auth_required(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """
    Decorator that marks a method as not requiring authentication.
    Useful for public endpoints or health checks.
    """

    @wraps(fn)
    async def wrapper(self, *args, **kwargs):
        ctx = getattr(self, "ctx", None)
        if ctx:
            ctx.logger.info("Making unauthenticated request")
        return await fn(self, *args, **kwargs)

    return wrapper


class ScopeValidator:
    """Helper class for validating OAuth scopes."""

    @staticmethod
    def validate_scopes(required_scopes: List[str], granted_scopes: List[str]) -> bool:
        """
        Validate that all required scopes are granted.

        Args:
            required_scopes: List of required scopes
            granted_scopes: List of granted scopes

        Returns:
            True if all required scopes are granted, False otherwise
        """
        return set(required_scopes).issubset(set(granted_scopes))

    @staticmethod
    def missing_scopes(required_scopes: List[str], granted_scopes: List[str]) -> List[str]:
        """
        Get list of missing scopes.

        Args:
            required_scopes: List of required scopes
            granted_scopes: List of granted scopes

        Returns:
            List of missing scopes
        """
        return list(set(required_scopes) - set(granted_scopes))


class TokenValidator:
    """Helper class for validating OAuth tokens."""

    @staticmethod
    def is_expired(expires_at: float) -> bool:
        """
        Check if a token is expired.

        Args:
            expires_at: Expiration timestamp

        Returns:
            True if token is expired, False otherwise
        """
        return time.time() >= expires_at

    @staticmethod
    def expires_soon(expires_at: float, buffer_seconds: int = 300) -> bool:
        """
        Check if a token expires soon.

        Args:
            expires_at: Expiration timestamp
            buffer_seconds: Buffer time in seconds

        Returns:
            True if token expires within buffer time, False otherwise
        """
        return time.time() + buffer_seconds >= expires_at 