"""
Authentication helpers for Agentic Fabric SDK.

Provides utilities for loading application credentials and creating
authenticated clients.
"""

from pathlib import Path
import json
import httpx
from typing import Optional, List, Dict
import logging

from ..fabriq_client import FabriqClient

logger = logging.getLogger(__name__)


class ApplicationNotFoundError(Exception):
    """Raised when an application configuration is not found."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


async def get_application_client(
    app_id: str,
    config_dir: Optional[Path] = None,
    gateway_url: Optional[str] = None,
) -> FabriqClient:
    """
    Get authenticated FabriqClient for an application.
    
    Automatically loads credentials from ~/.af/applications/{app_id}.json
    and exchanges them for a JWT token.
    
    Args:
        app_id: Application identifier (e.g., "my-slack-bot")
        config_dir: Optional custom config directory (default: ~/.af)
        gateway_url: Optional gateway URL override (default: from app config)
    
    Returns:
        Authenticated FabriqClient instance
    
    Raises:
        ApplicationNotFoundError: If application config doesn't exist
        AuthenticationError: If authentication fails
    
    Example:
        >>> client = await get_application_client("my-slack-bot")
        >>> result = await client.invoke_connection("my-slack", method="post_message", parameters={...})
    """
    # 1. Load application config
    try:
        app_config = load_application_config(app_id, config_dir)
    except FileNotFoundError as e:
        raise ApplicationNotFoundError(
            f"Application '{app_id}' not found. "
            f"Register it first with: afctl applications create --app-id {app_id} ..."
        ) from e
    
    # Use provided gateway_url or fall back to config
    base_url = gateway_url or app_config.get("gateway_url", "https://dashboard.agenticfabriq.com")
    
    # 2. Exchange credentials for JWT token
    try:
        async with httpx.AsyncClient() as http:
            response = await http.post(
                f"{base_url}/api/v1/applications/token",
                json={
                    "app_id": app_config["app_id"],
                    "secret_key": app_config["secret_key"]
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", response.text)
                except:
                    pass
                
                raise AuthenticationError(
                    f"Failed to authenticate application '{app_id}': {error_detail}"
                )
            
            token_data = response.json()
    except httpx.HTTPError as e:
        raise AuthenticationError(
            f"Network error while authenticating application '{app_id}': {e}"
        ) from e
    
    # 3. Create and return authenticated client
    client = FabriqClient(
        base_url=base_url,
        auth_token=token_data["access_token"]
    )
    
    # Store metadata for potential refresh
    client._app_id = app_id
    client._expires_in = token_data.get("expires_in", 86400)
    
    logger.info(
        f"Authenticated as application '{app_id}' "
        f"(user_id={token_data.get('user_id')}, tenant_id={token_data.get('tenant_id')})"
    )
    
    return client


def load_application_config(
    app_id: str,
    config_dir: Optional[Path] = None
) -> Dict:
    """
    Load application config from disk.
    
    Args:
        app_id: Application identifier
        config_dir: Optional custom config directory (default: ~/.af)
    
    Returns:
        Application configuration dictionary
    
    Raises:
        FileNotFoundError: If application config doesn't exist
    
    Example:
        >>> config = load_application_config("my-slack-bot")
        >>> print(config["app_id"], config["created_at"])
    """
    if config_dir is None:
        config_dir = Path.home() / ".af"
    
    app_file = config_dir / "applications" / f"{app_id}.json"
    
    if not app_file.exists():
        raise FileNotFoundError(
            f"Application '{app_id}' not found at {app_file}. "
            f"Register it with: afctl applications create --app-id {app_id}"
        )
    
    with open(app_file, "r") as f:
        return json.load(f)


def save_application_config(
    app_id: str,
    config: Dict,
    config_dir: Optional[Path] = None
) -> Path:
    """
    Save application config to disk.
    
    Args:
        app_id: Application identifier
        config: Application configuration dictionary
        config_dir: Optional custom config directory (default: ~/.af)
    
    Returns:
        Path to saved config file
    
    Example:
        >>> config = {
        ...     "app_id": "my-bot",
        ...     "secret_key": "sk_...",
        ...     "gateway_url": "https://dashboard.agenticfabriq.com"
        ... }
        >>> path = save_application_config("my-bot", config)
    """
    if config_dir is None:
        config_dir = Path.home() / ".af"
    
    # Create applications directory if it doesn't exist
    app_dir = config_dir / "applications"
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # Write config file
    app_file = app_dir / f"{app_id}.json"
    with open(app_file, "w") as f:
        json.dump(config, f, indent=2)
    
    # Secure the file (user read/write only)
    app_file.chmod(0o600)
    
    logger.info(f"Saved application config to {app_file}")
    
    return app_file


def list_applications(
    config_dir: Optional[Path] = None
) -> List[Dict]:
    """
    List all registered applications.
    
    Args:
        config_dir: Optional custom config directory (default: ~/.af)
    
    Returns:
        List of application configuration dictionaries
    
    Example:
        >>> apps = list_applications()
        >>> for app in apps:
        ...     print(f"{app['app_id']}: {app.get('name', 'N/A')}")
    """
    if config_dir is None:
        config_dir = Path.home() / ".af"
    
    app_dir = config_dir / "applications"
    
    if not app_dir.exists():
        return []
    
    apps = []
    for app_file in sorted(app_dir.glob("*.json")):
        try:
            with open(app_file, "r") as f:
                app_config = json.load(f)
                apps.append(app_config)
        except Exception as e:
            logger.warning(f"Failed to load application config from {app_file}: {e}")
    
    return apps


def delete_application_config(
    app_id: str,
    config_dir: Optional[Path] = None
) -> bool:
    """
    Delete application config from disk.
    
    Args:
        app_id: Application identifier
        config_dir: Optional custom config directory (default: ~/.af)
    
    Returns:
        True if deleted, False if not found
    
    Example:
        >>> deleted = delete_application_config("my-old-bot")
        >>> if deleted:
        ...     print("Deleted successfully")
    """
    if config_dir is None:
        config_dir = Path.home() / ".af"
    
    app_file = config_dir / "applications" / f"{app_id}.json"
    
    if not app_file.exists():
        return False
    
    app_file.unlink()
    logger.info(f"Deleted application config: {app_file}")
    
    return True

