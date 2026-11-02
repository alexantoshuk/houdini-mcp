"""
TCP JSON-lines bridge that runs inside Houdini / hython.

Start from a Python Shell or shelf:
    import houdini_mcp_bridge
    houdini_mcp_bridge.start_server(port=18812)

Or headless:
    hython houdini_mcp_bridge.py --port 18812
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import traceback
from typing import Any

PROTOCOL_VERSION = 1
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18812

_server_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _result(req_id: str, result: Any) -> dict[str, Any]:
    return {"v": PROTOCOL_VERSION, "id": req_id, "ok": True, "result": result}


def _error(req_id: str, message: str, code: str = "error") -> dict[str, Any]:
    return {
        "v": PROTOCOL_VERSION,
        "id": req_id,
        "ok": False,
        "error": {"code": code, "message": message},
    }


def _node_snapshot(node) -> dict[str, Any]:
    parms = {}
    try:
        for parm in node.parms() or []:
            try:
                parms[parm.name()] = parm.eval()
            except Exception:  # noqa: BLE001
                parms[parm.name()] = None
    except Exception:  # noqa: BLE001
        pass
    children = []
    try:
        children = [c.path() for c in node.children()]
    except Exception:  # noqa: BLE001
        pass
    inputs = []
    try:
        for idx, inp in enumerate(node.inputs() or []):
            if inp is not None:
                inputs.append({"from": inp.path(), "to_index": idx})
    except Exception:  # noqa: BLE001
        pass
    return {
        "path": node.path(),
        "name": node.name(),
        "type": node.type().name(),
        "category": node.type().category().name(),
        "parms": parms,
        "children": children,
        "inputs": inputs,
        "outputs": [],
    }


def _set_parm(node, parm_name: str, value: Any) -> None:
    parm = node.parm(parm_name)
    if parm is not None:
        parm.set(value)
        return
    parm_tuple = node.parmTuple(parm_name)
    if parm_tuple is None:
        raise ValueError(f"parm not found: {parm_name}")
    if isinstance(value, (list, tuple)):
        parm_tuple.set(list(value))
    else:
        parm_tuple.set([value] * len(parm_tuple))


def _handle(method: str, params: dict[str, Any]) -> Any:
    import hou  # type: ignore

    if method == "ping":
        return {
            "status": "ok",
            "backend": "houdini",
            "version": hou.applicationVersionString(),
        }

    if method == "get_scene_info":
        return {
            "hip_file": hou.hipFile.path(),
            "houdini_version": hou.applicationVersionString(),
            "fps": hou.fps(),
            "frame": hou.frame(),
            "node_count": len(hou.node("/").allSubChildren()),
            "backend": "houdini",
        }

    if method == "list_nodes":
        parent_path = params.get("path") or "/obj"
        recursive = bool(params.get("recursive", False))
        parent = hou.node(parent_path)
        if parent is None:
            raise ValueError(f"node not found: {parent_path}")
        if recursive:
            nodes = [parent] + list(parent.allSubChildren())
        else:
            nodes = list(parent.children())
        return [_node_snapshot(n) for n in nodes]

    if method == "get_node":
        node = hou.node(params["path"])
        if node is None:
            raise ValueError(f"node not found: {params['path']}")
        return _node_snapshot(node)

    if method == "create_node":
        parent = hou.node(params["parent"])
        if parent is None:
            raise ValueError(f"parent not found: {params['parent']}")
        node = parent.createNode(params["type"], node_name=params.get("name"))
        try:
            node.moveToGoodPosition()
        except Exception:  # noqa: BLE001
            pass
        return _node_snapshot(node)

    if method == "set_parm":
        node = hou.node(params["path"])
        if node is None:
            raise ValueError(f"node not found: {params['path']}")
        _set_parm(node, params["parm"], params["value"])
        return {"path": params["path"], "parm": params["parm"], "value": params["value"]}

    if method == "connect_nodes":
        src = hou.node(params["from_path"])
        dst = hou.node(params["to_path"])
        if src is None:
            raise ValueError(f"node not found: {params['from_path']}")
        if dst is None:
            raise ValueError(f"node not found: {params['to_path']}")
        dst.setInput(int(params.get("to_index", 0)), src, int(params.get("from_index", 0)))
        return {
            "from_path": src.path(),
            "to_path": dst.path(),
            "from_index": int(params.get("from_index", 0)),
            "to_index": int(params.get("to_index", 0)),
        }

    if method == "delete_node":
        path = params["path"]
        if path in ("/obj", "/", "/stage", "/out", "/ch", "/img", "/tasks", "/mat"):
            raise ValueError(f"refusing to delete protected path: {path}")
        node = hou.node(path)
        if node is None:
            raise ValueError(f"node not found: {path}")
        node_type = node.type().name()
        node.destroy()
        return {"deleted": path, "type": node_type}

    if method == "execute_python":
        code = params.get("code") or ""
        local_vars: dict[str, Any] = {"hou": hou}
        exec(compile(code, "<houdini-mcp>", "exec"), local_vars, local_vars)
        result = local_vars.get("result", local_vars.get("_"))
        return {"result": result, "backend": "houdini"}

    if method == "save_hip":
        path = params.get("path")
        if path:
            hou.hipFile.save(file_name=path)
        else:
            hou.hipFile.save()
        return {"hip_file": hou.hipFile.path(), "saved": True}

    if method == "load_hip":
        hou.hipFile.load(params["path"], suppress_save_prompt=True)
        return {"hip_file": hou.hipFile.path(), "loaded": True}

    if method == "list_node_types":
        category = params.get("category")
        categories = hou.nodeTypeCategories()
        items = []
        for cat_name, cat in categories.items():
            if category and cat_name.lower() != str(category).lower():
                continue
            for type_name, node_type in cat.nodeTypes().items():
                items.append(
                    {
                        "type": type_name,
                        "label": node_type.description(),
                        "category": cat_name,
                    }
                )
        return items[:500]

    if method == "search":
        query = (params.get("query") or "").lower().strip()
        results = []
        for cat_name, cat in hou.nodeTypeCategories().items():
            for type_name, node_type in cat.nodeTypes().items():
                label = node_type.description() or type_name
                blob = f"{type_name} {label} {cat_name}".lower()
                if query and query not in blob:
                    continue
                results.append(
                    {
                        "id": f"{cat_name}/{type_name}",
                        "title": f"{label} ({cat_name}/{type_name})",
                        "url": f"houdini://docs/node/{cat_name}/{type_name}",
                    }
                )
                if len(results) >= 50:
                    return {"results": results}
        return {"results": results}

    if method == "fetch":
        doc_id = params["id"]
        if "/" not in doc_id:
            raise ValueError("id must look like Category/type, e.g. Sop/box")
        cat_name, type_name = doc_id.split("/", 1)
        categories = hou.nodeTypeCategories()
        if cat_name not in categories:
            raise ValueError(f"unknown category: {cat_name}")
        node_type = categories[cat_name].nodeTypes().get(type_name)
        if node_type is None:
            raise ValueError(f"unknown node type: {doc_id}")
        help_text = ""
        try:
            help_text = node_type.help() or ""
        except Exception:  # noqa: BLE001
            help_text = node_type.description() or type_name
        return {
            "id": doc_id,
            "title": node_type.description() or type_name,
            "text": help_text,
            "url": f"houdini://docs/node/{cat_name}/{type_name}",
            "metadata": {"category": cat_name, "type": type_name},
        }

    raise ValueError(f"unknown method: {method}")


def _process_line(line: str) -> str:
    req_id = "unknown"
    try:
        req = json.loads(line)
        req_id = str(req.get("id", "unknown"))
        method = req.get("method")
        params = req.get("params") or {}
        if not method:
            return json.dumps(_error(req_id, "missing method", "bad_request"))
        result = _handle(method, params)
        return json.dumps(_result(req_id, result), default=str)
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            _error(req_id, f"{exc}\n{traceback.format_exc()}", "exception"),
            default=str,
        )


def _serve(host: str, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(32)
    sock.settimeout(1.0)
    print(f"[houdini-mcp] bridge listening on {host}:{port}", file=sys.stderr)
    try:
        while not _stop_event.is_set():
            try:
                conn, _addr = sock.accept()
            except socket.timeout:
                continue
            with conn:
                conn.settimeout(60.0)
                buf = b""
                while b"\n" not in buf:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                if not buf:
                    continue
                line = buf.decode("utf-8", errors="replace").splitlines()[0]
                response = _process_line(line) + "\n"
                conn.sendall(response.encode("utf-8"))
    finally:
        sock.close()


def start_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, background: bool = True) -> None:
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        print("[houdini-mcp] bridge already running", file=sys.stderr)
        return
    _stop_event.clear()
    if background:
        _server_thread = threading.Thread(
            target=_serve, args=(host, port), name="houdini-mcp-bridge", daemon=True
        )
        _server_thread.start()
    else:
        _serve(host, port)


def stop_server() -> None:
    _stop_event.set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Houdini MCP TCP bridge")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    start_server(host=args.host, port=args.port, background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
