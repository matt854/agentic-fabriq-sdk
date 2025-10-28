"""
Configuration management for the Agentic Fabric CLI.
"""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class CLIConfig(BaseModel):
    """CLI configuration model."""
    
        # Gateway settings (support environment variable override)
    gateway_url: str = Field(
        default_factory=lambda: os.getenv("AF_GATEWAY_URL", "https://dashboard.agenticfabriq.com"),
        description="Gateway URL"
    )
    
    # Keycloak settings (support environment variable override)
    keycloak_url: str = Field(
        default_factory=lambda: os.getenv("AF_KEYCLOAK_URL", "https://auth.agenticfabriq.com"),
        description="Keycloak URL"
    )
    keycloak_realm: str = Field(default="agentic-fabric", description="Keycloak realm")
    keycloak_client_id: str = Field(default="agentic-fabriq-cli", description="Keycloak client ID for CLI")
    
    # Authentication (deprecated - now stored in token_storage, kept for backward compatibility)
    access_token: Optional[str] = Field(default=None, description="Access token (deprecated)")
    refresh_token: Optional[str] = Field(default=None, description="Refresh token (deprecated)")
    token_expires_at: Optional[int] = Field(default=None, description="Token expiration timestamp (deprecated)")
    
    # Tenant settings
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID")
    
    # CLI settings
    config_file: str = Field(default="", description="Configuration file path")
    verbose: bool = Field(default=False, description="Verbose output")
    output_format: str = Field(default="table", description="Output format (table, json, yaml)")
    page_size: int = Field(default=20, description="Default page size for list commands")
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.config_file:
            self.config_file = self._get_default_config_path()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        home_dir = Path.home()
        config_dir = home_dir / ".af"
        return str(config_dir / "config.json")
    
    def load(self) -> None:
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                # Migrate old localhost URLs to production URLs
                needs_migration = False
                if data.get('gateway_url') in ['http://localhost:8000', 'localhost:8000']:
                    data['gateway_url'] = 'https://dashboard.agenticfabriq.com'
                    needs_migration = True
                    print("✨ Migrated gateway_url from localhost to dashboard.agenticfabriq.com")
                
                if data.get('keycloak_url') in ['http://localhost:8080', 'localhost:8080']:
                    data['keycloak_url'] = 'https://auth.agenticfabriq.com'
                    needs_migration = True
                    print("✨ Migrated keycloak_url from localhost to auth.agenticfabriq.com")
                    
                # Update fields from loaded data
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                
                # Save migrated config
                if needs_migration:
                    self.save()
                        
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_file}: {e}")
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Save configuration
            with open(self.config_file, 'w') as f:
                # Only save non-default values
                data = {}
                for key, value in self.dict().items():
                    if key in ['config_file', 'verbose']:
                        continue  # Skip runtime-only fields
                    if value is not None:
                        data[key] = value
                
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error: Failed to save config to {self.config_file}: {e}")
    
    def clear_auth(self) -> None:
        """Clear authentication tokens (deprecated - use token_storage)."""
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.save()
    
    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.
        
        This method is deprecated. Use token_storage for authentication checks.
        """
        # Check token storage first
        try:
            from af_cli.core.token_storage import get_token_storage
            token_storage = get_token_storage()
            token_data = token_storage.load()
            if token_data and not token_storage.is_token_expired(token_data):
                return True
        except Exception:
            pass
        
        # Fall back to config (backward compatibility)
        return self.access_token is not None
    
    def get_access_token(self) -> Optional[str]:
        """
        Get current access token, refreshing if necessary.
        
        Returns:
            Valid access token or None
        """
        try:
            from af_cli.core.token_storage import get_token_storage
            from af_cli.core.oauth import OAuth2Client
            
            token_storage = get_token_storage()
            token_data = token_storage.load()
            
            if not token_data:
                return None
            
            # Check if token is expired
            if token_storage.is_token_expired(token_data):
                # Try to refresh
                if token_data.refresh_token:
                    try:
                        oauth_client = OAuth2Client(
                            keycloak_url=self.keycloak_url,
                            realm=self.keycloak_realm,
                            client_id=self.keycloak_client_id
                        )
                        
                        new_tokens = oauth_client.refresh_token(token_data.refresh_token)
                        new_token_data = token_storage.extract_token_info(new_tokens)
                        
                        # Preserve tenant_id
                        if not new_token_data.tenant_id and token_data.tenant_id:
                            new_token_data.tenant_id = token_data.tenant_id
                        
                        # Save new tokens
                        token_storage.save(new_token_data)
                        
                        # Update config
                        self.access_token = new_token_data.access_token
                        self.refresh_token = new_token_data.refresh_token
                        self.token_expires_at = new_token_data.expires_at
                        self.save()
                        
                        return new_token_data.access_token
                        
                    except Exception:
                        # Refresh failed
                        return None
                else:
                    return None
            
            return token_data.access_token
            
        except Exception:
            # Fall back to config
            return self.access_token
    
    def get_headers(self) -> dict:
        """Get HTTP headers for API requests."""
        headers = {
            "Content-Type": "application/json",
        }
        
        # Get access token (with auto-refresh)
        access_token = self.get_access_token()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        if self.tenant_id:
            headers["X-Tenant-Id"] = self.tenant_id
        
        return headers


# Global configuration instance
_config: Optional[CLIConfig] = None


def get_config() -> CLIConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = CLIConfig()
        # Load existing config (with automatic migration)
        _config.load()
    return _config


def set_config(config: CLIConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
