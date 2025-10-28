"""
Configuration commands for the Agentic Fabric CLI.
"""

import typer

from af_cli.core.config import get_config
from af_cli.core.output import error, info, print_output, success

app = typer.Typer(help="Configuration commands")


@app.command()
def show(
    format: str = typer.Option(None, "--format", help="Output format (overrides configured default)"),
):
    """Show current configuration."""
    config = get_config()
    
    # Use provided format, or fall back to configured output_format
    display_format = format if format else config.output_format
    
    config_data = {
        "gateway_url": config.gateway_url,
        "keycloak_url": config.keycloak_url,
        "tenant_id": config.tenant_id or "Not set",
        "authenticated": "Yes" if config.is_authenticated() else "No",
        "config_file": config.config_file,
        "output_format": config.output_format,
        "page_size": config.page_size,
    }
    
    print_output(
        config_data,
        format_type=display_format,
        title="Configuration"
    )


@app.command()
def set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
):
    """Set configuration value."""
    config = get_config()
    
    # Note: tenant_id is not settable - it comes from authentication
    valid_keys = {
        "gateway_url": "gateway_url",
        "keycloak_url": "keycloak_url",
        "output_format": "output_format",
        "page_size": "page_size",
    }
    
    if key not in valid_keys:
        error(f"Invalid configuration key: {key}")
        error(f"Valid keys: {', '.join(valid_keys.keys())}")
        if key == "tenant_id":
            error("Note: tenant_id cannot be set manually. It comes from authentication.")
            error("Run 'afctl auth login' to authenticate with a specific tenant.")
        raise typer.Exit(1)
    
    # Set the value
    setattr(config, valid_keys[key], value)
    config.save()
    
    success(f"Configuration updated: {key} = {value}")


@app.command()
def get(
    key: str = typer.Argument(..., help="Configuration key"),
):
    """Get configuration value."""
    config = get_config()
    
    # All readable config keys
    valid_keys = {
        "gateway_url": "gateway_url",
        "keycloak_url": "keycloak_url",
        "keycloak_realm": "keycloak_realm",
        "keycloak_client_id": "keycloak_client_id",
        "tenant_id": "tenant_id",
        "output_format": "output_format",
        "page_size": "page_size",
        "config_file": "config_file",
        "verbose": "verbose",
        "authenticated": "is_authenticated",  # Special: calls method
    }
    
    if key not in valid_keys:
        error(f"Invalid configuration key: {key}")
        error(f"Valid keys: {', '.join(sorted(valid_keys.keys()))}")
        raise typer.Exit(1)
    
    # Handle special keys that are methods
    if key == "authenticated":
        value = "Yes" if config.is_authenticated() else "No"
    else:
        value = getattr(config, valid_keys[key])
    
    # Display value
    if value is None:
        info(f"{key}: (not set)")
    else:
        info(f"{key}: {value}")


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
):
    """Reset configuration to defaults."""
    config = get_config()
    
    if not yes and not typer.confirm("Are you sure you want to reset configuration to defaults?"):
        info("Reset cancelled")
        return
    
    # Clear authentication
    config.clear_auth()
    
    # Reset to defaults
    config.gateway_url = "https://dashboard.agenticfabriq.com"
    config.tenant_id = None
    config.output_format = "table"
    config.page_size = 20
    
    config.save()
    
    success("Configuration reset to defaults") 