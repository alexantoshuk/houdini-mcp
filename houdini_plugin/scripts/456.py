"""Start MCP bridge after the UI is ready (GUI only — skips hython)."""

from __future__ import annotations

import os
import sys


def _bootstrap() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
    if root not in sys.path:
        sys.path.insert(0, root)
    import houdini_mcp_bridge

    houdini_mcp_bridge.autostart_bridge()


try:
    _bootstrap()
except Exception as exc:  # noqa: BLE001
    print(f"[houdini-mcp] 456.py failed to start bridge: {exc}")
