# Houdini MCP for Zed

This extension exposes a local stdio MCP server that any Zed agent can use
(Zed Agent, Cursor, Claude ACP, Goose, Cline, OpenCode, Qwen Code, …).
Zed forwards configured MCP servers to External Agents over ACP.

## Setup

1. Install the Python package (once):

```powershell
pip install -e .
# or: pip install git+https://github.com/alexantoshuk/houdini-mcp.git
```

2. Install the Houdini bridge package (optional for live sessions):
   - Copy / link `houdini_plugin` into your Houdini packages folder, **or**
   - Run `scripts/install_houdini_package.ps1`
   - Restart Houdini — the bridge listens on `127.0.0.1:18812`

3. For offline / CI testing without Houdini, set `"mock": true` in the server settings.

## Verify

Open **Settings → AI → MCP Servers**. `Houdini MCP` should show a green
"Server is active" indicator.
