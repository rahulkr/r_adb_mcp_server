"""
ADB MCP Server - Enhanced Android Debug Bridge MCP Server for Flutter/Android Development
"""

from .server import mcp

__version__ = "0.1.0"

def main():
    """Entry point for the MCP server"""
    mcp.run()

__all__ = ["mcp", "main"]
