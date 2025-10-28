"""
CLI commands for managing registered applications.
"""

import json
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from af_cli.core.config import get_config
from af_cli.core.output import print_output

app = typer.Typer(help="Manage registered applications")
console = Console()


@app.command("register")
def register_application(
    app_id: str = typer.Option(..., "--app-id", help="Application identifier (no spaces)"),
    connections: str = typer.Option(..., "--connections", help="Tool connections (format: 'tool1:conn-id,tool2:conn-id')"),
    scopes: Optional[str] = typer.Option(None, "--scopes", help="Scopes (format: 'scope1,scope2,scope3')"),
):
    """
    Step 1: Register a new application (returns activation token).
    
    This registers your application and returns a temporary activation token
    that expires in 1 hour. Use this token with 'afctl applications connect'
    to complete the setup and save credentials locally.
    
    Example:
        afctl applications register \\
            --app-id my-slack-bot \\
            --connections slack:my-slack-conn,github:my-github-conn \\
            --scopes slack:read,slack:write,github:repo:read
    """
    config = get_config()
    
    if not config.is_authenticated():
        console.print("❌ Not authenticated. Run 'afctl auth login' first.", style="red")
        raise typer.Exit(1)
    
    # Parse connections
    tool_connections = {}
    if connections:
        for conn_pair in connections.split(","):
            try:
                tool, conn_id = conn_pair.split(":")
                tool_connections[conn_id] = []  # Will add scopes below
            except ValueError:
                console.print(f"❌ Invalid connection format: '{conn_pair}'. Use 'tool:conn-id'", style="red")
                raise typer.Exit(1)
    
    # Parse scopes and assign to connections
    if scopes:
        scope_list = [s.strip() for s in scopes.split(",")]
        # For simplicity, assign all scopes to all connections
        # In production, you might want per-connection scopes
        for conn_id in tool_connections:
            tool_connections[conn_id] = scope_list
    
    # Make API request to register (returns activation token)
    try:
        response = httpx.post(
            f"{config.gateway_url}/api/v1/applications/register",
            headers={"Authorization": f"Bearer {config.access_token}"},
            json={
                "app_id": app_id,
                "tool_connections": tool_connections
            },
            timeout=30.0
        )
        
        if response.status_code != 201:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("detail", response.text)
            except:
                pass
            
            console.print(f"❌ Failed to register application: {error_detail}", style="red")
            raise typer.Exit(1)
        
        data = response.json()
        
        # Display activation token
        console.print("\n✅ Application registered successfully!", style="green bold")
        console.print(f"\n📋 App ID: {data['app_id']}", style="cyan")
        console.print(f"\n🔑 Activation Token:", style="yellow bold")
        console.print(f"   {data['activation_token']}", style="yellow")
        console.print(f"\n⏰ Token expires: {data['expires_at'][:19]} UTC", style="white")
        console.print(f"   (Valid for 1 hour)", style="dim")
        
        console.print("\n📋 Next Steps:", style="cyan bold")
        console.print(f"   1. Navigate to your project directory", style="white")
        console.print(f"   2. Make sure you're authenticated: afctl auth login", style="white")
        console.print(f"   3. Run the connect command:", style="white")
        console.print(f"\n      afctl applications connect {app_id} --token <activation-token>", style="green")
        console.print(f"\n⚠️  Save the activation token! It expires in 1 hour and can only be used once.", style="yellow bold")
        
    except httpx.HTTPError as e:
        console.print(f"❌ Network error: {e}", style="red")
        raise typer.Exit(1)


@app.command("connect")
def connect_application(
    app_id: str = typer.Argument(..., help="Application identifier"),
    token: str = typer.Option(..., "--token", help="Activation token from registration"),
):
    """
    Step 2: Connect/activate an application (saves credentials locally).
    
    Uses the activation token from 'afctl applications register' to activate
    the application and save credentials to the current directory.
    
    Example:
        afctl applications connect my-slack-bot --token <activation-token>
    """
    config = get_config()
    
    if not config.is_authenticated():
        console.print("❌ Not authenticated. Run 'afctl auth login' first.", style="red")
        raise typer.Exit(1)
    
    # Make API request to activate (returns final credentials)
    try:
        response = httpx.post(
            f"{config.gateway_url}/api/v1/applications/activate",
            headers={"Authorization": f"Bearer {config.access_token}"},
            json={"activation_token": token},
            timeout=30.0
        )
        
        if response.status_code == 404:
            console.print("❌ Invalid or expired activation token", style="red")
            console.print("   The token may have expired (valid for 1 hour) or was already used.", style="yellow")
            console.print("   Register again with 'afctl applications register'", style="white")
            raise typer.Exit(1)
        elif response.status_code == 403:
            console.print("❌ This activation token does not belong to you", style="red")
            raise typer.Exit(1)
        elif response.status_code != 201:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("detail", response.text)
            except:
                pass
            
            console.print(f"❌ Failed to activate application: {error_detail}", style="red")
            raise typer.Exit(1)
        
        data = response.json()
        
        # Save credentials locally
        from af_sdk import save_application_config
        
        app_config = {
            "app_id": data["app_id"],
            "secret_key": data["secret_key"],
            "user_id": data["user_id"],
            "tenant_id": data["tenant_id"],
            "tool_connections": data["tool_connections"],
            "created_at": data["created_at"],
            "gateway_url": config.gateway_url
        }
        
        app_file = save_application_config(data["app_id"], app_config)
        
        # Display success
        console.print("\n✅ Application activated successfully!", style="green bold")
        console.print(f"\n📋 App ID: {data['app_id']}", style="cyan")
        console.print(f"🔑 Secret Key: {data['secret_key']}", style="yellow")
        console.print(f"\n💾 Credentials saved to: {app_file}", style="green")
        console.print("\n⚠️  Save the secret key securely! It won't be shown again.", style="yellow bold")
        console.print("\n🚀 Your agent can now authenticate with:", style="cyan")
        console.print(f"   from af_sdk import get_application_client", style="white")
        console.print(f"   client = await get_application_client('{data['app_id']}')", style="white")
        
    except httpx.HTTPError as e:
        console.print(f"❌ Network error: {e}", style="red")
        raise typer.Exit(1)


@app.command("list")
def list_applications(
    format: str = typer.Option("table", "--format", help="Output format (table, json, yaml)"),
    sync: bool = typer.Option(True, "--sync/--no-sync", help="Sync with server and remove orphaned local files"),
):
    """
    List all registered applications.
    
    Shows applications from local config files (~/.af/applications/) and optionally
    syncs with the server to remove any local files for applications that have been
    deleted from the server (e.g., via the UI).
    """
    config = get_config()
    
    # Load from local config first
    from af_sdk import list_applications as list_local_apps, delete_application_config
    
    local_apps = list_local_apps()
    
    # If sync is enabled and user is authenticated, check server and clean up orphans
    if sync and config.is_authenticated():
        try:
            response = httpx.get(
                f"{config.gateway_url}/api/v1/applications",
                headers={"Authorization": f"Bearer {config.access_token}"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                server_apps = data.get("applications", [])
                server_app_ids = {app["app_id"] for app in server_apps}
                
                # Find and remove orphaned local files
                orphaned = []
                for local_app in local_apps[:]:  # Copy list to modify during iteration
                    if local_app["app_id"] not in server_app_ids:
                        orphaned.append(local_app["app_id"])
                        # Delete orphaned local config
                        delete_application_config(local_app["app_id"])
                        # Remove from local_apps list
                        local_apps.remove(local_app)
                
                if orphaned:
                    console.print(f"🧹 Cleaned up {len(orphaned)} orphaned local file(s): {', '.join(orphaned)}", style="yellow")
            
        except httpx.HTTPError as e:
            # If server check fails, just show local apps with a warning
            console.print(f"⚠️  Could not sync with server: {e}", style="yellow")
        except Exception as e:
            # Silently continue if sync fails
            pass
    
    if format == "table":
        if not local_apps:
            console.print("No applications registered.", style="yellow")
            return
        
        table = Table(title="Registered Applications")
        table.add_column("App ID", style="cyan")
        table.add_column("Created", style="green")
        table.add_column("Tool Connections", style="magenta")
        table.add_column("Config File", style="white")
        
        for app in local_apps:
            conn_count = len(app.get("tool_connections", {}))
            conn_str = f"{conn_count} connection(s)"
            config_file = f"~/.af/applications/{app['app_id']}.json"
            
            table.add_row(
                app["app_id"],
                app.get("created_at", "N/A")[:10],  # Just date
                conn_str,
                config_file
            )
        
        console.print(table)
        console.print(f"\n📊 Total: {len(local_apps)} application(s)")
    else:
        print_output(
            {"applications": local_apps, "total": len(local_apps)},
            format_type=format,
            title="Registered Applications"
        )


@app.command("show")
def show_application(
    app_id: str = typer.Argument(..., help="Application identifier"),
    reveal_secret: bool = typer.Option(False, "--reveal-secret", help="Reveal the secret key"),
):
    """
    Show details of a registered application.
    
    Example:
        afctl applications show my-slack-bot
        afctl applications show my-slack-bot --reveal-secret
    """
    from af_sdk import load_application_config, ApplicationNotFoundError
    
    try:
        app_config = load_application_config(app_id)
    except ApplicationNotFoundError as e:
        console.print(f"❌ {e}", style="red")
        raise typer.Exit(1)
    
    console.print(f"\n📋 Application: {app_config['app_id']}", style="cyan bold")
    console.print(f"👤 User ID: {app_config.get('user_id', 'N/A')}", style="white")
    console.print(f"🏢 Tenant ID: {app_config.get('tenant_id', 'N/A')}", style="white")
    console.print(f"📅 Created: {app_config.get('created_at', 'N/A')}", style="white")
    console.print(f"🌐 Gateway: {app_config.get('gateway_url', 'N/A')}", style="white")
    
    if reveal_secret:
        console.print(f"\n🔑 Secret Key: {app_config['secret_key']}", style="yellow bold")
        console.print("⚠️  Keep this secret secure!", style="yellow")
    else:
        console.print(f"\n🔑 Secret Key: ••••••••", style="white")
        console.print("   Use --reveal-secret to show", style="dim")
    
    console.print("\n🔌 Tool Connections:", style="cyan bold")
    tool_conns = app_config.get("tool_connections", {})
    if tool_conns:
        for conn_id, scopes in tool_conns.items():
            console.print(f"  • {conn_id}", style="white")
            if scopes:
                console.print(f"    Scopes: {', '.join(scopes)}", style="dim")
    else:
        console.print("  (none)", style="dim")
    
    config_file = Path.home() / ".af" / "applications" / f"{app_id}.json"
    console.print(f"\n💾 Config file: {config_file}", style="green")


@app.command("delete")
def delete_application(
    app_id: str = typer.Argument(..., help="Application identifier"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
):
    """
    Delete a registered application.
    
    This will:
    - Delete the application registration on the server
    - Remove local credentials
    - Invalidate all active tokens
    
    Example:
        afctl applications delete my-slack-bot
        afctl applications delete my-slack-bot --yes
    """
    config = get_config()
    
    if not config.is_authenticated():
        console.print("❌ Not authenticated. Run 'afctl auth login' first.", style="red")
        raise typer.Exit(1)
    
    # Confirm deletion
    if not yes:
        console.print(f"\n⚠️  This will:", style="yellow bold")
        console.print(f"  • Delete the application registration on the server", style="white")
        console.print(f"  • Remove local credentials from ~/.af/applications/{app_id}.json", style="white")
        console.print(f"  • Invalidate all active tokens for this application", style="white")
        
        confirm = typer.confirm(f"\nAre you sure you want to delete '{app_id}'?", default=False)
        if not confirm:
            console.print("❌ Cancelled", style="yellow")
            raise typer.Exit(0)
    
    # Delete from server
    try:
        response = httpx.delete(
            f"{config.gateway_url}/api/v1/applications/{app_id}",
            headers={"Authorization": f"Bearer {config.access_token}"},
            timeout=30.0
        )
        
        if response.status_code == 404:
            console.print(f"⚠️  Application '{app_id}' not found on server", style="yellow")
        elif response.status_code != 204:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("detail", response.text)
            except:
                pass
            
            console.print(f"❌ Failed to delete from server: {error_detail}", style="red")
            raise typer.Exit(1)
        else:
            console.print(f"✅ Deleted from server", style="green")
        
    except httpx.HTTPError as e:
        console.print(f"❌ Network error: {e}", style="red")
        raise typer.Exit(1)
    
    # Delete local config
    from af_sdk import delete_application_config
    
    deleted = delete_application_config(app_id)
    if deleted:
        console.print(f"✅ Deleted local credentials", style="green")
    else:
        console.print(f"⚠️  Local credentials not found", style="yellow")
    
    console.print(f"\n🎉 Application '{app_id}' deleted successfully", style="green bold")


@app.command("test")
def test_application(
    app_id: str = typer.Argument(..., help="Application identifier"),
):
    """
    Test application authentication.
    
    Attempts to exchange credentials for a token to verify the application
    is properly registered and can authenticate.
    
    Example:
        afctl applications test my-slack-bot
    """
    import asyncio
    from af_sdk import get_application_client, ApplicationNotFoundError, AuthenticationError
    
    async def _test():
        try:
            console.print(f"🔄 Testing authentication for '{app_id}'...", style="cyan")
            
            client = await get_application_client(app_id)
            
            console.print(f"✅ Authentication successful!", style="green bold")
            console.print(f"\n📋 Application: {client._app_id}", style="cyan")
            console.print(f"⏱️  Token expires in: {client._expires_in} seconds", style="white")
            console.print(f"\n🎉 Your application can authenticate and make API calls!", style="green")
            
        except ApplicationNotFoundError as e:
            console.print(f"❌ {e}", style="red")
            raise typer.Exit(1)
        except AuthenticationError as e:
            console.print(f"❌ {e}", style="red")
            raise typer.Exit(1)
    
    asyncio.run(_test())

