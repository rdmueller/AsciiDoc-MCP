"""Main entry point for dacli MCP server.

This module provides the CLI entry point for running the MCP server.
The server can be configured via command line arguments or environment variables.

Usage:
    uv run dacli-mcp --docs-root /path/to/docs

    Or with environment variable:
    PROJECT_PATH=/path/to/docs uv run dacli-mcp

MCP Client Configuration (e.g., Claude Desktop):
    {
        "mcpServers": {
            "dacli": {
                "command": "uv",
                "args": ["run", "dacli-mcp"],
                "cwd": "/path/to/dacli",
                "env": {"PROJECT_PATH": "/path/to/documentation"}
            }
        }
    }
"""

import argparse
import os
import sys
from pathlib import Path

from dacli import __version__
from dacli.mcp_app import create_mcp_server


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="dacli-mcp",
        description="dacli MCP server - LLM interaction with documentation",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--docs-root",
        type=str,
        default=None,
        help="Root directory containing documentation files. "
        "Can also be set via PROJECT_PATH environment variable.",
    )
    return parser


def get_docs_root(args_docs_root: str | None) -> Path:
    """Determine the documentation root directory.

    Priority:
    1. Command line argument (--docs-root)
    2. PROJECT_PATH environment variable
    3. Current working directory

    Args:
        args_docs_root: Value from command line argument (may be None)

    Returns:
        Resolved path to documentation root
    """
    if args_docs_root is not None:
        return Path(args_docs_root).resolve()

    env_path = os.environ.get("PROJECT_PATH")
    if env_path:
        return Path(env_path).resolve()

    return Path.cwd()


def main() -> int:
    """Main entry point.

    Creates and runs the MCP server with stdio transport.
    """
    parser = create_parser()
    args = parser.parse_args()

    docs_root = get_docs_root(args.docs_root)

    # Validate docs root exists
    if not docs_root.exists():
        print(f"Error: Documentation root does not exist: {docs_root}", file=sys.stderr)
        return 1

    if not docs_root.is_dir():
        print(f"Error: Documentation root is not a directory: {docs_root}", file=sys.stderr)
        return 1

    # Create and run MCP server
    mcp = create_mcp_server(docs_root=docs_root)

    # Run with stdio transport (default for MCP)
    mcp.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
