"""
Main CLI application for Agentic Fabric.
"""

import os
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from af_cli.commands.applications import app as applications_app
from af_cli.commands.auth import app as auth_app
from af_cli.commands.config import app as config_app
from af_cli.commands.tools import app as tools_app
from af_cli.core.config import get_config
from af_cli.core.output import success, error, info

app = typer.Typer(
    name="af",
    help="Agentic Fabric CLI - Manage your connectivity hub",
    add_completion=False,
)

console = Console()

# Add subcommands
app.add_typer(auth_app, name="auth", help="Authentication commands")
app.add_typer(config_app, name="config", help="Configuration commands")
app.add_typer(tools_app, name="tools", help="Tool management commands")
app.add_typer(applications_app, name="applications", help="Application management commands")


@app.command()
def version():
    """Show version information."""
    from af_cli import __version__
    console.print(f"Agentic Fabric CLI v{__version__}")


@app.command()
def status():
    """Show system status and configuration."""
    config = get_config()
    
    # Create status table
    table = Table(title="Agentic Fabric Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    # Check gateway connection
    try:
        import httpx
        response = httpx.get(f"{config.gateway_url}/health", timeout=5.0)
        if response.status_code == 200:
            table.add_row("Gateway", "✅ Online", config.gateway_url)
        else:
            table.add_row("Gateway", "❌ Error", f"Status: {response.status_code}")
    except Exception as e:
        table.add_row("Gateway", "❌ Offline", str(e))
    
    # Check authentication
    if config.access_token:
        table.add_row("Authentication", "✅ Authenticated", f"Tenant: {config.tenant_id}")
    else:
        table.add_row("Authentication", "❌ Not authenticated", "Run 'afctl auth login'")
    
    # Check configuration
    config_path = config.config_file
    if os.path.exists(config_path):
        table.add_row("Configuration", "✅ Found", config_path)
    else:
        table.add_row("Configuration", "❌ Not found", config_path)
    
    console.print(table)


@app.command()
def init(
    gateway_url: str = typer.Option(
        "https://dashboard.agenticfabriq.com",
        "--gateway-url",
        help="Gateway URL"
    ),
    tenant_id: Optional[str] = typer.Option(
        None,
        "--tenant-id",
        help="Tenant ID"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Skip confirmation and overwrite existing config"
    ),
):
    """Initialize CLI configuration."""
    config = get_config()
    
    # Check if config exists
    if os.path.exists(config.config_file) and not yes:
        error(f"Configuration already exists at {config.config_file}")
        error("Use --yes to overwrite")
        raise typer.Exit(1)
    
    # Create config directory if it doesn't exist
    os.makedirs(os.path.dirname(config.config_file), exist_ok=True)
    
    # Save configuration
    config.gateway_url = gateway_url
    if tenant_id:
        config.tenant_id = tenant_id
    
    config.save()
    
    success(f"Configuration initialized at {config.config_file}")
    info(f"Gateway URL: {gateway_url}")
    if tenant_id:
        info(f"Tenant ID: {tenant_id}")
    else:
        info("Run 'afctl auth login' to authenticate")


@app.callback()
def main(
    ctx: typer.Context,
    config_file: Optional[str] = typer.Option(
        None,
        "--config",
        help="Path to configuration file"
    ),
    gateway_url: Optional[str] = typer.Option(
        None,
        "--gateway-url",
        help="Gateway URL"
    ),
    tenant_id: Optional[str] = typer.Option(
        None,
        "--tenant-id",
        help="Tenant ID"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose output"
    ),
):
    """
    Agentic Fabric CLI - Manage your connectivity hub.
    
    The CLI provides commands for managing tool connections and applications
    in your Agentic Fabric deployment.
    """
    # Configure global options
    config = get_config()
    
    if config_file:
        config.config_file = config_file
    
    # Load configuration
    config.load()
    
    # Override with command line options
    if gateway_url:
        config.gateway_url = gateway_url
    if tenant_id:
        config.tenant_id = tenant_id
    
    config.verbose = verbose
    
    # Store config in context
    ctx.obj = config


if __name__ == "__main__":
    app() 