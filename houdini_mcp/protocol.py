"""Shared JSON-lines bridge protocol between MCP server and Houdini."""

from __future__ import annotations

from typing import Any

PROTOCOL_VERSION = 1
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18812


def make_request(req_id: str, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "v": PROTOCOL_VERSION,
        "id": req_id,
        "method": method,
        "params": params or {},
    }


def make_result(req_id: str, result: Any) -> dict[str, Any]:
    return {"v": PROTOCOL_VERSION, "id": req_id, "ok": True, "result": result}


def make_error(req_id: str, error: str, code: str = "error") -> dict[str, Any]:
    return {
        "v": PROTOCOL_VERSION,
        "id": req_id,
        "ok": False,
        "error": {"code": code, "message": error},
    }
