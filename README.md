# Houdini MCP

OpenAI-compatible [Model Context Protocol](https://modelcontextprotocol.io) server for **SideFX Houdini**.

Repository: [github.com/alexantoshuk/houdini-mcp](https://github.com/alexantoshuk/houdini-mcp)

Works with **any agent path available in Zed**:

| Agent path | How it gets the tools |
| --- | --- |
| Zed Agent | Uses Zed `context_servers` / this extension directly |
| External Agents (Cursor, Claude ACP, Goose, Cline, OpenCode, Qwen Code, …) | Zed forwards configured MCP servers over ACP |
| Terminal / other MCP clients | `python -m houdini_mcp` (stdio) or Streamable HTTP |

## Architecture

```
Zed agents  --stdio MCP-->  houdini-mcp (Python)
                               |
                               +-- mock backend (tests / offline)
                               +-- TCP JSON-lines --> Houdini bridge (hou.*)
```

## Quick start

```powershell
pip install -e .
python -m houdini_mcp --mock   # offline smoke
```

### Zed

```powershell
.\scripts\install_zed.ps1
```

Then in Zed: **Extensions → Install Dev Extension** → select this repo folder.

Or add manually to `%APPDATA%\Zed\settings.json`:

```json
"context_servers": {
  "houdini-mcp": {
    "command": "C:/Python310/python.exe",
    "args": ["-m", "houdini_mcp"],
    "env": {
      "HOUDINI_MCP_HOST": "127.0.0.1",
      "HOUDINI_MCP_PORT": "18812"
    }
  }
}
```

Green status under **Settings → AI → MCP Servers** means the server is active for all Zed agents.

### Live Houdini

```powershell
.\scripts\install_houdini_package.ps1
```

Restart Houdini. The bridge autostarts on `127.0.0.1:18812` via `scripts/123.py` / `456.py` — **GUI sessions only**. `hython` / `hbatch` skip the bind so they no longer steal the port from a live Houdini (no more renaming hooks to `.bak`).

Manual start / recovery inside Houdini Python Shell:

```python
import houdini_mcp_bridge
houdini_mcp_bridge.ensure_bridge()  # preferred — no-op if already listening
# or: houdini_mcp_bridge.start_server(port=18812)
```

| Env | Effect |
| --- | --- |
| `HOUDINI_MCP_NO_BRIDGE=1` | Never autostart |
| `HOUDINI_MCP_BRIDGE=1` | Force autostart even in hython |

## Tools (OpenAI-style)

Focused tools with input schemas + safety annotations (`readOnlyHint` / `destructiveHint`):

- `get_scene_info`, `list_nodes`, `get_node`
- `create_node`, `set_parameter`, `connect_nodes`, `delete_node`
- `execute_python`, `save_hip`, `load_hip`, `list_node_types`
- OpenAI company-knowledge pair: `search`, `fetch`
- Workflow skills: `list_skills`, `get_skill` — load `SKILL.md` from the **public** repo
  [`alexantoshuk/houdini-mcp`](https://github.com/alexantoshuk/houdini-mcp)
  (`raw.githubusercontent.com` / Contents API, ref `main`). Local `.cursor/skills/` is offline fallback only.

Also exposes resources `houdini://scene/info`, `houdini://skills/index`, and prompt `houdini_starter_network`.

| Env | Meaning |
| --- | --- |
| `HOUDINI_MCP_SKILLS_REPO` | GitHub `owner/repo` (default `alexantoshuk/houdini-mcp`) |
| `HOUDINI_MCP_SKILLS_REF` | Branch/tag/commit (default `main`) |
| `HOUDINI_MCP_SKILLS_SOURCE` | `auto` (github→local), `github`, or `local` |

MCP `instructions` tell the agent to call `get_skill(...)` when the task matches. Push skill edits to `main` before expecting remote agents to see them.

## Transports

| Transport | Command | Use |
| --- | --- | --- |
| stdio (default) | `python -m houdini_mcp` | Zed, Claude Desktop, Cursor, Codex |
| Streamable HTTP | `python -m houdini_mcp --transport streamable-http` | OpenAI remote MCP / Inspector |

## Tests

```powershell
pip install -e ".[dev]"
pytest -q
```

## Skills (Cursor / agents)

Project skills live in `.cursor/skills/houdini-*/SKILL.md` (33 skills):

- **Solaris / assets / model / VEX** — `houdini-solaris`, `houdini-assets`, `houdini-model`, `houdini-vex`
- **Sims** — pyro, fluid, vellum, destruction, mpm, ocean, grains, …
- **Pipeline** — tops, io, render, shade, character, crowds, …
- **Defaults** — `houdini-discipline` (senior operating rules)

Index + attribution: [`skills/README.md`](skills/README.md).  
Upstream guides (MIT): [`skills/vendor/fxhoudinimcp/`](skills/vendor/fxhoudinimcp/).

## Environment

| Variable | Meaning |
| --- | --- |
| `HOUDINI_MCP_HOST` | Bridge host (default `127.0.0.1`) |
| `HOUDINI_MCP_PORT` | Bridge port (default `18812`) |
| `HOUDINI_MCP_NO_BRIDGE` | `1` → skip autostart hooks |
| `HOUDINI_MCP_BRIDGE` | `1` → force autostart in hython too |
| `HOUDINI_MCP_MOCK` | `1` → in-process mock scene |
| `HOUDINI_MCP_TRANSPORT` | `stdio` / `streamable-http` |
