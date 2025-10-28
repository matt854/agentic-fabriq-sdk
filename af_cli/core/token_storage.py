"""
Secure token storage for Agentic Fabric CLI.

This module provides secure storage for authentication tokens using the system keychain
(macOS Keychain, Windows Credential Manager, Linux Secret Service) with fallback to
encrypted file storage.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    keyring = None

import jwt
from cryptography.fernet import Fernet
from pydantic import BaseModel


class TokenData(BaseModel):
    """Token data model."""
    
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: int  # Unix timestamp
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


class TokenStorage:
    """Secure token storage using system keychain or encrypted files."""
    
    SERVICE_NAME = "agentic-fabriq-cli"
    ACCOUNT_NAME = "default"
    
    def __init__(self, use_keyring: bool = True):
        """
        Initialize token storage.
        
        Args:
            use_keyring: Whether to use system keyring (falls back to file if unavailable)
        """
        self.use_keyring = use_keyring and KEYRING_AVAILABLE
        self.config_dir = Path.home() / ".af"
        self.token_file = self.config_dir / "tokens.enc"
        self.key_file = self.config_dir / ".key"
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    def _get_encryption_key(self) -> bytes:
        """
        Get or create encryption key for file storage.
        
        Returns:
            Fernet encryption key
        """
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(self.key_file, 0o600)
            return key
    
    def save(self, token_data: TokenData) -> None:
        """
        Save token data securely.
        
        Args:
            token_data: Token data to save
        """
        # Serialize token data
        token_json = token_data.json()
        
        if self.use_keyring:
            # Use system keyring
            try:
                keyring.set_password(
                    self.SERVICE_NAME,
                    self.ACCOUNT_NAME,
                    token_json
                )
                return
            except Exception as e:
                # Fall back to file storage
                print(f"Warning: Keyring storage failed, using file storage: {e}")
                self.use_keyring = False
        
        # Fall back to encrypted file storage
        key = self._get_encryption_key()
        fernet = Fernet(key)
        
        encrypted_data = fernet.encrypt(token_json.encode('utf-8'))
        
        with open(self.token_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Set restrictive permissions
        os.chmod(self.token_file, 0o600)
    
    def load(self) -> Optional[TokenData]:
        """
        Load token data.
        
        Returns:
            Token data if available, None otherwise
        """
        token_json = None
        
        if self.use_keyring:
            # Try system keyring first
            try:
                token_json = keyring.get_password(
                    self.SERVICE_NAME,
                    self.ACCOUNT_NAME
                )
            except Exception:
                # Fall back to file storage
                self.use_keyring = False
        
        if not token_json and self.token_file.exists():
            # Try encrypted file storage
            try:
                key = self._get_encryption_key()
                fernet = Fernet(key)
                
                with open(self.token_file, 'rb') as f:
                    encrypted_data = f.read()
                
                token_json = fernet.decrypt(encrypted_data).decode('utf-8')
            except Exception as e:
                print(f"Warning: Failed to load tokens from file: {e}")
                return None
        
        if token_json:
            try:
                return TokenData.parse_raw(token_json)
            except Exception as e:
                print(f"Warning: Failed to parse token data: {e}")
                return None
        
        return None
    
    def delete(self) -> None:
        """Delete stored token data."""
        if self.use_keyring:
            # Delete from keyring
            try:
                keyring.delete_password(
                    self.SERVICE_NAME,
                    self.ACCOUNT_NAME
                )
            except Exception:
                pass
        
        # Delete file storage
        if self.token_file.exists():
            try:
                self.token_file.unlink()
            except Exception:
                pass
    
    def is_token_expired(self, token_data: Optional[TokenData] = None) -> bool:
        """
        Check if token is expired.
        
        Args:
            token_data: Token data to check (loads from storage if not provided)
            
        Returns:
            True if token is expired or invalid
        """
        if token_data is None:
            token_data = self.load()
        
        if not token_data:
            return True
        
        # Add 60 second buffer to account for clock skew
        return time.time() >= (token_data.expires_at - 60)
    
    def parse_jwt_claims(self, access_token: str) -> Dict:
        """
        Parse JWT token claims without validation.
        
        Args:
            access_token: JWT access token
            
        Returns:
            Dictionary of claims
        """
        try:
            # Decode without verification (we trust the token from Keycloak)
            claims = jwt.decode(
                access_token,
                options={"verify_signature": False}
            )
            return claims
        except Exception:
            return {}
    
    def extract_token_info(self, tokens: Dict) -> TokenData:
        """
        Extract and parse token information.
        
        Args:
            tokens: Token response from OAuth endpoint
            
        Returns:
            Structured token data
        """
        access_token = tokens['access_token']
        refresh_token = tokens.get('refresh_token')
        expires_in = tokens.get('expires_in', 3600)
        
        # Calculate expiration time
        expires_at = int(time.time()) + expires_in
        
        # Parse JWT claims
        claims = self.parse_jwt_claims(access_token)
        
        # Extract user info from claims
        tenant_id = claims.get('tenant_id') or claims.get('tenant')
        user_id = claims.get('sub')
        email = claims.get('email')
        name = claims.get('name') or claims.get('preferred_username')
        
        return TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            tenant_id=tenant_id,
            user_id=user_id,
            email=email,
            name=name
        )


# Global token storage instance
_token_storage: Optional[TokenStorage] = None


def get_token_storage() -> TokenStorage:
    """Get the global token storage instance."""
    global _token_storage
    if _token_storage is None:
        _token_storage = TokenStorage()
    return _token_storage

