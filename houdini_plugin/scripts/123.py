"""Auto-start the Houdini MCP bridge when a GUI session finishes loading."""

try:
    import houdini_mcp_bridge

    houdini_mcp_bridge.start_server(port=18812, background=True)
except Exception as exc:  # noqa: BLE001
    print(f"[houdini-mcp] failed to autostart bridge: {exc}")
