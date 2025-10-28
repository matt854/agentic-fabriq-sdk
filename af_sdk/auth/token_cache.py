"""
Token cache manager for OAuth tokens.
"""

import asyncio
from typing import Dict, List, Optional

from ..exceptions import AuthenticationError, TokenRefreshError
from ..models.types import OAuthToken
from .oauth import ScopeValidator, TokenValidator


class VaultClient:
    """Client for interacting with the vault service."""

    def __init__(self, base_url: str, http_client, logger):
        self.base_url = base_url
        self.http_client = http_client
        self.logger = logger

    async def read_secret(self, path: str) -> Optional[Dict]:
        """Read a secret from the vault."""
        try:
            response = await self.http_client.get(f"{self.base_url}/api/secrets/{path}")
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                response.raise_for_status()
        except Exception as e:
            self.logger.error(f"Failed to read secret from vault: {e}")
            raise

    async def write_secret(self, path: str, data: Dict) -> None:
        """Write a secret to the vault."""
        try:
            response = await self.http_client.post(
                f"{self.base_url}/api/secrets",
                json={"path": path, "data": data}
            )
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f"Failed to write secret to vault: {e}")
            raise

    async def delete_secret(self, path: str) -> None:
        """Delete a secret from the vault."""
        try:
            response = await self.http_client.delete(f"{self.base_url}/api/secrets/{path}")
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f"Failed to delete secret from vault: {e}")
            raise


class TokenManager:
    """Handles per-user OAuth token lifecycle."""

    def __init__(self, tenant_id: str, vault_client: VaultClient, gateway_client=None):
        self.tenant_id = tenant_id
        self.vault_client = vault_client
        self.gateway_client = gateway_client
        self.cache: Dict[str, OAuthToken] = {}
        self.lock = asyncio.Lock()
        self.refresh_locks: Dict[str, asyncio.Lock] = {}

    async def get_oauth_token(
        self,
        tool_id: str,
        user_id: Optional[str],
        scopes: List[str],
        refresh_if_expired: bool = True,
    ) -> str:
        """
        Get a valid OAuth token for the specified tool and user.

        Args:
            tool_id: ID of the tool requiring authentication
            user_id: ID of the user (None for service accounts)
            scopes: Required OAuth scopes
            refresh_if_expired: Whether to refresh expired tokens

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If token is not available or invalid
            TokenRefreshError: If token refresh fails
        """
        cache_key = f"{tool_id}:{user_id or 'service'}"
        
        # Check cache first
        token = self.cache.get(cache_key)
        if token and not TokenValidator.is_expired(token.expires_at.timestamp()):
            # Validate scopes
            if ScopeValidator.validate_scopes(scopes, token.scopes):
                return token.access_token
            else:
                missing = ScopeValidator.missing_scopes(scopes, token.scopes)
                raise AuthenticationError(f"Insufficient scopes. Missing: {missing}")

        # Get or create refresh lock for this token
        if cache_key not in self.refresh_locks:
            self.refresh_locks[cache_key] = asyncio.Lock()
        
        refresh_lock = self.refresh_locks[cache_key]

        async with refresh_lock:
            # Double-check after acquiring lock
            token = self.cache.get(cache_key)
            if token and not TokenValidator.is_expired(token.expires_at.timestamp()):
                if ScopeValidator.validate_scopes(scopes, token.scopes):
                    return token.access_token

            # Load token from vault
            secret_path = self._get_token_path(tool_id, user_id)
            try:
                secret_data = await self.vault_client.read_secret(secret_path)
                if not secret_data:
                    raise AuthenticationError(f"No OAuth token found for {tool_id}")

                token = OAuthToken(**secret_data)
                
                # Check if token is expired
                if TokenValidator.is_expired(token.expires_at.timestamp()):
                    if refresh_if_expired and token.refresh_token:
                        token = await self._refresh_token(tool_id, user_id, token)
                    else:
                        raise AuthenticationError(f"OAuth token expired for {tool_id}")

                # Validate scopes
                if not ScopeValidator.validate_scopes(scopes, token.scopes):
                    missing = ScopeValidator.missing_scopes(scopes, token.scopes)
                    raise AuthenticationError(f"Insufficient scopes. Missing: {missing}")

                # Cache the token
                self.cache[cache_key] = token
                return token.access_token

            except Exception as e:
                if isinstance(e, (AuthenticationError, TokenRefreshError)):
                    raise
                raise AuthenticationError(f"Failed to get OAuth token: {e}")

    async def _refresh_token(
        self, tool_id: str, user_id: Optional[str], token: OAuthToken
    ) -> OAuthToken:
        """
        Refresh an OAuth token using the refresh token.

        Args:
            tool_id: ID of the tool
            user_id: ID of the user
            token: Current token with refresh_token

        Returns:
            New token with updated access_token and expires_at

        Raises:
            TokenRefreshError: If refresh fails
        """
        if not self.gateway_client:
            raise TokenRefreshError("Gateway client not configured")

        if not token.refresh_token:
            raise TokenRefreshError("No refresh token available")

        try:
            # Call gateway to refresh token
            response = await self.gateway_client.post(
                "/token/refresh",
                json={
                    "refresh_token": token.refresh_token,
                    "tool_id": tool_id,
                    "user_id": user_id,
                }
            )
            response.raise_for_status()
            
            refresh_data = response.json()
            
            # Create new token
            new_token = OAuthToken(
                access_token=refresh_data["access_token"],
                refresh_token=refresh_data.get("refresh_token", token.refresh_token),
                token_type=refresh_data.get("token_type", "Bearer"),
                expires_at=refresh_data["expires_at"],
                scopes=refresh_data.get("scopes", token.scopes),
            )

            # Store in vault
            secret_path = self._get_token_path(tool_id, user_id)
            await self.vault_client.write_secret(secret_path, new_token.dict())

            return new_token

        except Exception as e:
            raise TokenRefreshError(f"Failed to refresh token: {e}")

    async def store_oauth_token(
        self, tool_id: str, user_id: Optional[str], token: OAuthToken
    ) -> None:
        """
        Store an OAuth token in the vault and cache.

        Args:
            tool_id: ID of the tool
            user_id: ID of the user
            token: OAuth token to store
        """
        secret_path = self._get_token_path(tool_id, user_id)
        await self.vault_client.write_secret(secret_path, token.dict())

        # Update cache
        cache_key = f"{tool_id}:{user_id or 'service'}"
        self.cache[cache_key] = token

    async def revoke_oauth_token(self, tool_id: str, user_id: Optional[str]) -> None:
        """
        Revoke an OAuth token (remove from vault and cache).

        Args:
            tool_id: ID of the tool
            user_id: ID of the user
        """
        secret_path = self._get_token_path(tool_id, user_id)
        await self.vault_client.delete_secret(secret_path)

        # Remove from cache
        cache_key = f"{tool_id}:{user_id or 'service'}"
        self.cache.pop(cache_key, None)

    async def list_tokens(self, user_id: Optional[str]) -> List[Dict]:
        """
        List all tokens for a user.

        Args:
            user_id: ID of the user

        Returns:
            List of token metadata
        """
        # This would need to be implemented based on vault capabilities
        # For now, return cached tokens
        result = []
        user_key = user_id or 'service'
        
        for cache_key, token in self.cache.items():
            if cache_key.endswith(f":{user_key}"):
                tool_id = cache_key.split(":")[0]
                result.append({
                    "tool_id": tool_id,
                    "user_id": user_id,
                    "scopes": token.scopes,
                    "expires_at": token.expires_at.isoformat(),
                    "is_expired": TokenValidator.is_expired(token.expires_at.timestamp()),
                })
        
        return result

    def _get_token_path(self, tool_id: str, user_id: Optional[str]) -> str:
        """
        Get the vault path for a token.

        Args:
            tool_id: ID of the tool
            user_id: ID of the user

        Returns:
            Vault path for the token
        """
        user_part = user_id or "service"
        return f"af/{self.tenant_id}/{user_part}/oauth/{tool_id}/token"

    async def cleanup_expired_tokens(self) -> None:
        """Remove expired tokens from cache."""
        expired_keys = []
        
        for cache_key, token in self.cache.items():
            if TokenValidator.is_expired(token.expires_at.timestamp()):
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.cache[key]

    async def get_token_info(self, tool_id: str, user_id: Optional[str]) -> Optional[Dict]:
        """
        Get information about a token without returning the actual token.

        Args:
            tool_id: ID of the tool
            user_id: ID of the user

        Returns:
            Token information or None if not found
        """
        cache_key = f"{tool_id}:{user_id or 'service'}"
        token = self.cache.get(cache_key)
        
        if not token:
            # Try to load from vault
            secret_path = self._get_token_path(tool_id, user_id)
            secret_data = await self.vault_client.read_secret(secret_path)
            if secret_data:
                token = OAuthToken(**secret_data)
        
        if token:
            return {
                "tool_id": tool_id,
                "user_id": user_id,
                "scopes": token.scopes,
                "expires_at": token.expires_at.isoformat(),
                "is_expired": TokenValidator.is_expired(token.expires_at.timestamp()),
                "expires_soon": TokenValidator.expires_soon(token.expires_at.timestamp()),
            }
        
        return None 