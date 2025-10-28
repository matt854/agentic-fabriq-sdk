"""
Authentication commands for the Agentic Fabric CLI.

This module provides OAuth2/PKCE-based authentication commands for secure
login without requiring client secrets.
"""

import time
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from af_cli.core.config import get_config
from af_cli.core.oauth import OAuth2Client
from af_cli.core.output import error, info, success, warning
from af_cli.core.token_storage import TokenData, get_token_storage

app = typer.Typer(help="Authentication commands")
console = Console()


def get_oauth_client(keycloak_url: Optional[str] = None) -> OAuth2Client:
    """
    Get configured OAuth2 client.
    
    Args:
        keycloak_url: Override Keycloak URL from config
        
    Returns:
        Configured OAuth2Client instance
    """
    config = get_config()
    
    # Get Keycloak URL from environment or config
    keycloak_url = keycloak_url or config.dict().get('keycloak_url', 'https://auth.agenticfabriq.com')
    realm = config.dict().get('keycloak_realm', 'agentic-fabric')
    client_id = config.dict().get('keycloak_client_id', 'agentic-fabriq-cli')
    
    return OAuth2Client(
        keycloak_url=keycloak_url,
        realm=realm,
        client_id=client_id,
        scopes=['openid', 'profile', 'email']
    )


@app.command()
def login(
    tenant_id: Optional[str] = typer.Option(
        None,
        "--tenant-id",
        help="Tenant ID (optional, can be extracted from JWT)"
    ),
    keycloak_url: Optional[str] = typer.Option(
        None,
        "--keycloak-url",
        help="Keycloak URL (default: https://auth.agenticfabriq.com or from config)"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Skip confirmation when already authenticated"
    ),
):
    """
    Login to Agentic Fabric using OAuth2/PKCE flow.
    
    This command will open your default browser and prompt you to authenticate
    with your Keycloak credentials. Once authenticated, your tokens will be
    securely stored for future use.
    """
    config = get_config()
    token_storage = get_token_storage()
    
    # Check if already authenticated
    existing_token = token_storage.load()
    if existing_token and not token_storage.is_token_expired(existing_token):
        user_display = existing_token.email or existing_token.name or existing_token.user_id
        info(f"Already authenticated as: {user_display}")
        info(f"Tenant: {existing_token.tenant_id or 'Unknown'}")
        
        if not yes and not typer.confirm("Do you want to login again?"):
            return
    
    try:
        # Get OAuth2 client
        oauth_client = get_oauth_client(keycloak_url)
        
        # Perform login
        console.print()
        # Always open browser for authentication
        tokens = oauth_client.login(open_browser=True, timeout=300, use_hosted_callback=False)
        
        # Extract and save token data
        token_data = token_storage.extract_token_info(tokens)
        
        # Override tenant_id if provided, otherwise use default for Keycloak JWTs
        if tenant_id:
            token_data.tenant_id = tenant_id
        elif not token_data.tenant_id:
            # Keycloak JWTs don't have tenant_id, use the same default as the backend
            token_data.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Save tokens
        token_storage.save(token_data)
        
        # Update config
        config.access_token = token_data.access_token
        config.refresh_token = token_data.refresh_token
        config.token_expires_at = token_data.expires_at
        config.tenant_id = token_data.tenant_id  # Always set tenant_id
        config.save()
        
        # Display success message
        console.print()
        success("Successfully authenticated!")
        
        if token_data.name or token_data.email:
            user_display = f"{token_data.name}" if token_data.name else ""
            if token_data.email:
                user_display += f" ({token_data.email})" if user_display else token_data.email
            info(f"User: {user_display}")
        
        if token_data.tenant_id:
            info(f"Tenant: {token_data.tenant_id}")
        
        expires_in = token_data.expires_at - int(time.time())
        info(f"Token expires in {expires_in // 60} minutes")
        
    except Exception as e:
        console.print()
        error(f"Authentication failed: {e}")
        raise typer.Exit(1)


@app.command()
def logout(
    keycloak_url: Optional[str] = typer.Option(
        None,
        "--keycloak-url",
        help="Keycloak URL (default: https://auth.agenticfabriq.com or from config)"
    ),
):
    """
    Logout from Agentic Fabric.
    
    This command will revoke your tokens and clear your local authentication state.
    """
    config = get_config()
    token_storage = get_token_storage()
    
    # Load tokens
    token_data = token_storage.load()
    
    if not token_data:
        warning("Not authenticated")
        return
    
    try:
        # Revoke tokens with Keycloak
        if token_data.refresh_token:
            oauth_client = get_oauth_client(keycloak_url)
            oauth_client.logout(token_data.refresh_token)
        
    except Exception as e:
        warning(f"Server logout failed (continuing with local logout): {e}")
    
    # Clear local tokens
    token_storage.delete()
    config.clear_auth()
    
    success("Successfully logged out")


@app.command()
def status():
    """
    Show authentication status and token information.
    
    Displays current authentication state, user information, and token expiration.
    """
    config = get_config()
    token_storage = get_token_storage()
    
    # Load token data
    token_data = token_storage.load()
    
    if not token_data:
        warning("Not authenticated")
        info("Run 'afctl auth login' to authenticate")
        return
    
    # Create status table
    table = Table(title="Authentication Status", show_header=False)
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="white")
    
    # Authentication status
    is_expired = token_storage.is_token_expired(token_data)
    if is_expired:
        table.add_row("Status", "[red]Expired[/red]")
    else:
        table.add_row("Status", "[green]✓ Authenticated[/green]")
    
    # User information
    if token_data.name:
        table.add_row("Name", token_data.name)
    if token_data.email:
        table.add_row("Email", token_data.email)
    if token_data.user_id:
        table.add_row("User ID", token_data.user_id)
    if token_data.tenant_id:
        table.add_row("Tenant ID", token_data.tenant_id)
    
    # Token expiration
    if token_data.expires_at:
        expires_in = token_data.expires_at - int(time.time())
        if expires_in > 0:
            minutes = expires_in // 60
            seconds = expires_in % 60
            table.add_row("Expires in", f"{minutes}m {seconds}s")
        else:
            table.add_row("Expired", f"{-expires_in // 60} minutes ago")
    
    # Refresh token availability
    if token_data.refresh_token:
        table.add_row("Refresh Token", "[green]Available[/green]")
    else:
        table.add_row("Refresh Token", "[red]Not available[/red]")
    
    # Gateway URL
    if config.gateway_url:
        table.add_row("Gateway URL", config.gateway_url)
    
    console.print()
    console.print(table)
    console.print()
    
    # Show recommendations
    if is_expired:
        if token_data.refresh_token:
            info("Token has expired. Run 'afctl auth refresh' to get a new token")
        else:
            info("Token has expired. Run 'afctl auth login' to re-authenticate")


@app.command()
def refresh(
    keycloak_url: Optional[str] = typer.Option(
        None,
        "--keycloak-url",
        help="Keycloak URL (default: https://auth.agenticfabriq.com or from config)"
    ),
):
    """
    Refresh authentication token.
    
    Uses the refresh token to obtain a new access token without requiring
    interactive login.
    """
    config = get_config()
    token_storage = get_token_storage()
    
    # Load tokens
    token_data = token_storage.load()
    
    if not token_data or not token_data.refresh_token:
        error("No refresh token available")
        info("Run 'afctl auth login' to authenticate")
        raise typer.Exit(1)
    
    try:
        # Get OAuth2 client
        oauth_client = get_oauth_client(keycloak_url)
        
        # Refresh tokens
        info("Refreshing token...")
        new_tokens = oauth_client.refresh_token(token_data.refresh_token)
        
        # Extract and save new token data
        new_token_data = token_storage.extract_token_info(new_tokens)
        
        # Preserve tenant_id if not in new token
        if not new_token_data.tenant_id and token_data.tenant_id:
            new_token_data.tenant_id = token_data.tenant_id
        
        # Save new tokens
        token_storage.save(new_token_data)
        
        # Update config
        config.access_token = new_token_data.access_token
        config.refresh_token = new_token_data.refresh_token
        config.token_expires_at = new_token_data.expires_at
        config.save()
        
        success("Token refreshed successfully")
        
        expires_in = new_token_data.expires_at - int(time.time())
        info(f"New token expires in {expires_in // 60} minutes")
        
    except Exception as e:
        error(f"Token refresh failed: {e}")
        error("Please run 'afctl auth login' to re-authenticate")
        
        # Clear invalid tokens
        token_storage.delete()
        config.clear_auth()
        
        raise typer.Exit(1)


@app.command()
def token(
    show_full: bool = typer.Option(
        False,
        "--full",
        help="Show full token (warning: sensitive information)"
    ),
):
    """
    Display current access token.
    
    Use --full to see the complete token (warning: contains sensitive information).
    """
    config = get_config()
    token_storage = get_token_storage()
    
    # Load token data
    token_data = token_storage.load()
    
    if not token_data:
        error("Not authenticated")
        raise typer.Exit(1)
    
    if show_full:
        console.print("\n[bold yellow]Warning: Sensitive information below[/bold yellow]\n")
        console.print(f"Access token: {token_data.access_token}\n")
    else:
        # Show truncated token
        token_preview = token_data.access_token[:50] + "..." if len(token_data.access_token) > 50 else token_data.access_token
        console.print(f"\nAccess token: {token_preview}\n")
        info("Use --full to see complete token")
    
    # Check expiration
    if token_storage.is_token_expired(token_data):
        warning("Token has expired")
    else:
        expires_in = token_data.expires_at - int(time.time())
        info(f"Expires in: {expires_in // 60} minutes")


@app.command()
def whoami():
    """
    Display information about the currently authenticated user.
    """
    token_storage = get_token_storage()
    
    # Load token data
    token_data = token_storage.load()
    
    if not token_data:
        warning("Not authenticated")
        info("Run 'afctl auth login' to authenticate")
        return
    
    # Create user info table
    table = Table(title="Current User", show_header=False)
    table.add_column("Field", style="cyan", width=15)
    table.add_column("Value", style="white")
    
    if token_data.name:
        table.add_row("Name", token_data.name)
    if token_data.email:
        table.add_row("Email", token_data.email)
    if token_data.user_id:
        table.add_row("User ID", token_data.user_id)
    if token_data.tenant_id:
        table.add_row("Tenant", token_data.tenant_id)
    
    console.print()
    console.print(table)
    console.print()
