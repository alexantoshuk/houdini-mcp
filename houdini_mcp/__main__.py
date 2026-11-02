"""CLI entry: python -m houdini_mcp [--transport stdio|streamable-http] [--mock]."""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Houdini MCP server (OpenAI-compatible)")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "sse"),
        default=os.environ.get("HOUDINI_MCP_TRANSPORT", "stdio"),
        help="MCP transport (default: stdio for Zed / local agents)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use in-process mock Houdini backend (no live session required)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOUDINI_MCP_HOST"),
        help="Houdini bridge host (default 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("HOUDINI_MCP_PORT", "18812")),
        help="Houdini bridge port (default 18812)",
    )
    args = parser.parse_args(argv)

    if args.mock:
        os.environ["HOUDINI_MCP_MOCK"] = "1"
    if args.host:
        os.environ["HOUDINI_MCP_HOST"] = args.host
    if args.port:
        os.environ["HOUDINI_MCP_PORT"] = str(args.port)

    # Import after env is set so backend selector sees flags.
    from .server import run

    try:
        run(args.transport)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
