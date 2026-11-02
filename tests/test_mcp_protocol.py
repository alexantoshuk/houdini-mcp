"""Protocol tests for houdini-mcp (mock backend, no live Houdini required)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["HOUDINI_MCP_MOCK"] = "1"

from mcp import Client  # noqa: E402
from mcp.client.stdio import StdioServerParameters  # noqa: E402

from houdini_mcp.backend import reset_backend  # noqa: E402
from houdini_mcp.mock_backend import MockHoudiniBackend  # noqa: E402


@pytest.fixture(autouse=True)
def _reset():
    reset_backend()
    yield
    reset_backend()


def test_mock_backend_scene_flow():
    b = MockHoudiniBackend()
    info = b.handle("get_scene_info", {})
    assert info["backend"] == "mock"
    geo = b.handle("create_node", {"parent": "/obj", "type": "geo", "name": "geo1"})
    assert geo["path"] == "/obj/geo1"
    box = b.handle("create_node", {"parent": "/obj/geo1", "type": "box", "name": "box1"})
    null = b.handle("create_node", {"parent": "/obj/geo1", "type": "null", "name": "OUT"})
    b.handle(
        "connect_nodes",
        {"from_path": box["path"], "to_path": null["path"]},
    )
    nodes = b.handle("list_nodes", {"path": "/obj/geo1", "recursive": True})
    paths = {n["path"] for n in nodes}
    assert "/obj/geo1/box1" in paths
    search = b.handle("search", {"query": "box"})
    assert any(r["id"] == "box" for r in search["results"])
    doc = b.handle("fetch", {"id": "box"})
    assert doc["title"]


@pytest.mark.asyncio
async def test_mcp_initialize_and_tools():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "houdini_mcp", "--mock"],
        env={**os.environ, "HOUDINI_MCP_MOCK": "1"},
    )
    async with Client(params) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools.tools}
        required = {
            "get_scene_info",
            "list_nodes",
            "create_node",
            "set_parameter",
            "connect_nodes",
            "delete_node",
            "execute_python",
            "search",
            "fetch",
        }
        missing = required - names
        assert not missing, f"missing tools: {missing}"

        # Annotations should be present for OpenAI-style safety metadata.
        by_name = {t.name: t for t in tools.tools}
        assert by_name["get_scene_info"].annotations is not None
        assert by_name["get_scene_info"].annotations.read_only_hint is True
        assert by_name["delete_node"].annotations.destructive_hint is True

        result = await client.call_tool("get_scene_info", {})
        assert result.is_error is False
        text = ""
        for block in result.content:
            if getattr(block, "type", None) == "text" or block.__class__.__name__ == "TextContent":
                text = getattr(block, "text", "") or text
        payload = json.loads(text) if text.startswith("{") else (result.structured_content or {})
        # structured_content may wrap the dict return directly
        if "ok" not in payload and isinstance(result.structured_content, dict):
            payload = result.structured_content
        assert payload.get("ok") is True
        assert payload["result"]["backend"] == "mock"

        created = await client.call_tool(
            "create_node",
            {"parent": "/obj", "type": "geo", "name": "geo_test"},
        )
        assert created.is_error is False

        searched = await client.call_tool("search", {"query": "box"})
        assert searched.is_error is False

        fetched = await client.call_tool("fetch", {"id": "box"})
        assert fetched.is_error is False


@pytest.mark.asyncio
async def test_mcp_prompts_and_resources():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "houdini_mcp", "--mock"],
        env={**os.environ, "HOUDINI_MCP_MOCK": "1"},
    )
    async with Client(params) as client:
        prompts = await client.list_prompts()
        assert any(p.name == "houdini_starter_network" for p in prompts.prompts)
        resources = await client.list_resources()
        uris = [str(r.uri) for r in resources.resources]
        assert any(u.startswith("houdini://scene/info") for u in uris)
