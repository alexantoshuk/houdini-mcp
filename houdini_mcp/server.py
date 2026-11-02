"""OpenAI-compatible MCP server exposing Houdini scene tools."""

from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations

from . import __version__
from .backend import get_backend
from .bridge_client import BridgeError

INSTRUCTIONS = (
    "Houdini MCP controls a SideFX Houdini session through typed tools. "
    "Call get_scene_info first to confirm connectivity. Prefer create_node / "
    "set_parameter / connect_nodes over raw execute_python. Use search and fetch "
    "for node-type documentation. Destructive tools require care; never delete /obj."
)

mcp = MCPServer(
    "houdini-mcp",
    instructions=INSTRUCTIONS,
)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _call(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        result = get_backend().call(method, params)
        return {"ok": True, "result": result}
    except BridgeError as exc:
        return {"ok": False, "error": {"code": exc.code, "message": str(exc)}}
    except OSError as exc:
        return {
            "ok": False,
            "error": {
                "code": "connection_failed",
                "message": (
                    f"Cannot reach Houdini bridge ({exc}). "
                    "Start the bridge in Houdini (MCP shelf / 123.py) or set "
                    "HOUDINI_MCP_MOCK=1 for offline mock mode."
                ),
            },
        }


@mcp.tool(
    title="Get scene info",
    description="Use when you need Houdini session status: hip path, version, frame, fps.",
    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False),
)
def get_scene_info() -> dict[str, Any]:
    return _call("get_scene_info")


@mcp.tool(
    title="List nodes",
    description="List child nodes under a parent path. Set recursive=true to walk descendants.",
    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False),
)
def list_nodes(path: str = "/obj", recursive: bool = False) -> dict[str, Any]:
    return _call("list_nodes", {"path": path, "recursive": recursive})


@mcp.tool(
    title="Get node",
    description="Fetch details for one node: type, parms, inputs, outputs, children.",
    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False),
)
def get_node(path: str) -> dict[str, Any]:
    return _call("get_node", {"path": path})


@mcp.tool(
    title="Create node",
    description="Create a Houdini node under parent. Example: parent=/obj, type=geo, name=geo1.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False),
)
def create_node(parent: str, type: str, name: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"parent": parent, "type": type}
    if name:
        params["name"] = name
    return _call("create_node", params)


@mcp.tool(
    title="Set parameter",
    description="Set a parameter on a node. Value may be number, string, or list for multi-component parms.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False, idempotent_hint=True),
)
def set_parameter(path: str, parm: str, value: Any) -> dict[str, Any]:
    return _call("set_parm", {"path": path, "parm": parm, "value": value})


@mcp.tool(
    title="Connect nodes",
    description="Wire an output of from_path into an input of to_path.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False),
)
def connect_nodes(
    from_path: str,
    to_path: str,
    from_index: int = 0,
    to_index: int = 0,
) -> dict[str, Any]:
    return _call(
        "connect_nodes",
        {
            "from_path": from_path,
            "to_path": to_path,
            "from_index": from_index,
            "to_index": to_index,
        },
    )


@mcp.tool(
    title="Delete node",
    description="Delete a node and its descendants. Refuses to delete /obj.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False),
)
def delete_node(path: str) -> dict[str, Any]:
    return _call("delete_node", {"path": path})


@mcp.tool(
    title="Execute Python",
    description="Run Python in the Houdini process with hou available. Prefer typed tools when possible.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False),
)
def execute_python(code: str) -> dict[str, Any]:
    return _call("execute_python", {"code": code})


@mcp.tool(
    title="Save hip",
    description="Save the current hip file. Provide path to save-as; omit to save current file.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False),
)
def save_hip(path: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if path:
        params["path"] = path
    return _call("save_hip", params)


@mcp.tool(
    title="Load hip",
    description="Load a hip file into the current Houdini session.",
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False),
)
def load_hip(path: str) -> dict[str, Any]:
    return _call("load_hip", {"path": path})


@mcp.tool(
    title="List node types",
    description="List available Houdini node types, optionally filtered by category (Object, Sop, Dop, ...).",
    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False),
)
def list_node_types(category: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if category:
        params["category"] = category
    return _call("list_node_types", params)


@mcp.tool(
    name="search",
    title="Search Houdini docs",
    description="OpenAI-compatible search over node-type documentation. Returns id/title/url results.",
    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False),
)
def search(query: str) -> dict[str, Any]:
    payload = _call("search", {"query": query})
    if not payload.get("ok"):
        return payload
    # Company-knowledge shape: one text content item with JSON results.
    return {
        "ok": True,
        "result": payload["result"],
        "content_text": _json(payload["result"]),
    }


@mcp.tool(
    name="fetch",
    title="Fetch Houdini doc",
    description="OpenAI-compatible fetch of a documentation item by id from search results.",
    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False),
)
def fetch(id: str) -> dict[str, Any]:
    payload = _call("fetch", {"id": id})
    if not payload.get("ok"):
        return payload
    return {
        "ok": True,
        "result": payload["result"],
        "content_text": _json(payload["result"]),
    }


@mcp.resource("houdini://scene/info")
def scene_info_resource() -> str:
    """Current scene summary resource."""
    return _json(_call("get_scene_info"))


@mcp.prompt(
    name="houdini_starter_network",
    title="Starter SOP network",
    description="Guide for building a simple geo → box → null network under /obj.",
)
def houdini_starter_network() -> str:
    return (
        "1. Call get_scene_info to verify the bridge.\n"
        "2. create_node(parent='/obj', type='geo', name='geo1').\n"
        "3. create_node(parent='/obj/geo1', type='box', name='box1').\n"
        "4. create_node(parent='/obj/geo1', type='null', name='OUT').\n"
        "5. connect_nodes(from_path='/obj/geo1/box1', to_path='/obj/geo1/OUT').\n"
        "6. list_nodes(path='/obj/geo1', recursive=true) to verify."
    )


def create_server() -> MCPServer:
    return mcp


def run(transport: str | None = None) -> None:
    chosen = (transport or os.environ.get("HOUDINI_MCP_TRANSPORT") or "stdio").lower()
    if chosen in {"http", "streamable-http", "streamable_http"}:
        # OpenAI remote / Inspector style endpoint.
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
