"""
Output formatting utilities for the Agentic Fabric CLI.
"""

import json
from typing import Any, Dict, List, Optional

import yaml
from rich.console import Console
from rich.table import Table

from af_cli.core.config import get_config

console = Console()


def success(message: str) -> None:
    """Print success message."""
    console.print(f"✅ {message}", style="green")


def error(message: str) -> None:
    """Print error message."""
    console.print(f"❌ {message}", style="red")


def warning(message: str) -> None:
    """Print warning message."""
    console.print(f"⚠️ {message}", style="yellow")


def info(message: str) -> None:
    """Print info message."""
    console.print(f"ℹ️ {message}", style="blue")


def debug(message: str) -> None:
    """Print debug message if verbose mode is enabled."""
    config = get_config()
    if config.verbose:
        console.print(f"🔍 {message}", style="dim")


def print_table(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    title: Optional[str] = None,
) -> None:
    """Print data as a table."""
    if not data:
        warning("No data to display")
        return
    
    # Use provided columns or infer from first row
    if columns is None:
        columns = list(data[0].keys())
    
    # Create table with expand to fill terminal width and show grid lines
    table = Table(title=title, expand=True, show_lines=True)
    
    # Add columns with no_wrap to prevent text wrapping
    for column in columns:
        table.add_column(column.replace("_", " ").title(), style="cyan", no_wrap=True)
    
    # Add rows
    for row in data:
        table.add_row(*[str(row.get(col, "")) for col in columns])
    
    console.print(table)


def print_json(data: Any) -> None:
    """Print data as JSON."""
    console.print_json(json.dumps(data, indent=2, default=str))


def print_yaml(data: Any) -> None:
    """Print data as YAML."""
    console.print(yaml.dump(data, default_flow_style=False))


def print_output(
    data: Any,
    format_type: Optional[str] = None,
    columns: Optional[List[str]] = None,
    title: Optional[str] = None,
) -> None:
    """Print output in the specified format."""
    config = get_config()
    format_type = format_type or config.output_format
    
    if format_type == "json":
        print_json(data)
    elif format_type == "yaml":
        print_yaml(data)
    elif format_type == "table":
        if isinstance(data, list):
            print_table(data, columns, title)
        else:
            # Convert single item to table format
            if isinstance(data, dict):
                table_data = [{"Field": k, "Value": v} for k, v in data.items()]
                print_table(table_data, ["Field", "Value"], title)
            else:
                console.print(str(data))
    else:
        console.print(str(data))


def print_status(
    resource_type: str,
    resource_id: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Print resource status."""
    status_color = {
        "created": "green",
        "updated": "blue",
        "deleted": "red",
        "error": "red",
        "warning": "yellow",
    }.get(status, "white")
    
    message = f"{resource_type} {resource_id} {status}"
    console.print(message, style=status_color)
    
    if details and get_config().verbose:
        for key, value in details.items():
            console.print(f"  {key}: {value}", style="dim")


def prompt_confirm(message: str, default: bool = False) -> bool:
    """Prompt for confirmation."""
    default_text = "Y/n" if default else "y/N"
    response = console.input(f"{message} [{default_text}]: ")
    
    if not response:
        return default
    
    return response.lower() in ["y", "yes"]


def prompt_input(message: str, default: Optional[str] = None) -> str:
    """Prompt for input."""
    if default:
        message = f"{message} [{default}]"
    
    response = console.input(f"{message}: ")
    
    if not response and default:
        return default
    
    return response


def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp


def format_size(size: int) -> str:
    """Format file size for display."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}PB"


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text for display."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..." 