"""
Agentic Fabric CLI Tool

A command-line interface for managing Agentic Fabric resources including
agents, tools, and administrative operations.
"""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("agentic-fabriq-sdk")
    except PackageNotFoundError:
        # Fallback if package is not installed
        __version__ = "0.0.0-dev"
except ImportError:
    # Fallback for Python < 3.8 (though we require 3.11+)
    __version__ = "0.0.0-dev" 