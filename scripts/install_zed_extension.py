"""Install / refresh the houdini-mcp Zed extension into the local extensions dir."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WASM = ROOT / "target" / "wasm32-wasip1" / "release" / "houdini_mcp_zed.wasm"
EXT_DIR = Path.home().parent  # unused placeholder


def main() -> None:
    local = Path.home() / "AppData" / "Local" / "Zed" / "extensions"
    # Windows: LOCALAPPDATA
    import os

    local = Path(os.environ["LOCALAPPDATA"]) / "Zed" / "extensions"
    installed = local / "installed" / "houdini-mcp"
    installed.mkdir(parents=True, exist_ok=True)

    if not WASM.exists():
        raise SystemExit(f"missing wasm: {WASM} (run cargo build --release --target wasm32-wasip1)")

    shutil.copy2(WASM, installed / "extension.wasm")
    (installed / "extension.toml").write_text(
        """id = "houdini-mcp"
name = "Houdini MCP Server"
version = "0.1.0"
schema_version = 1
description = "OpenAI-compatible Model Context Protocol server for SideFX Houdini"
repository = "https://github.com/alexantoshuk/houdini-mcp"
authors = ["Alex Antoshuk"]
themes = []
icon_themes = []
languages = []
capabilities = []

[lib]
kind = "Rust"
version = "0.7.0"

[grammars]

[language_servers]

[context_servers.houdini-mcp]

[slash_commands]
""",
        encoding="utf-8",
    )

    cfg = installed / "configuration"
    cfg.mkdir(exist_ok=True)
    for name in ("installation_instructions.md", "default_settings.jsonc"):
        shutil.copy2(ROOT / "configuration" / name, cfg / name)

    index_path = local / "index.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    data.setdefault("extensions", {})["houdini-mcp"] = {
        "manifest": {
            "id": "houdini-mcp",
            "name": "Houdini MCP Server",
            "version": "0.1.0",
            "schema_version": 1,
            "description": "OpenAI-compatible Model Context Protocol server for SideFX Houdini",
            "repository": "https://github.com/alexantoshuk/houdini-mcp",
            "authors": ["Alex Antoshuk"],
            "lib": {"kind": "Rust", "version": "0.7.0"},
            "themes": [],
            "icon_themes": [],
            "languages": [],
            "grammars": {},
            "language_servers": {},
            "context_servers": {"houdini-mcp": {}},
            "slash_commands": {},
            "snippets": None,
            "capabilities": [],
        },
        "dev": True,
    }
    index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Installed extension -> {installed}")
    print(f"wasm bytes: {(installed / 'extension.wasm').stat().st_size}")


if __name__ == "__main__":
    main()
