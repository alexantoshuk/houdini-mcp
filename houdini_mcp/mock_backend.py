"""In-process mock Houdini scene for protocol tests without a live Houdini session."""

from __future__ import annotations

import copy
import threading
import time
from typing import Any


class MockHoudiniBackend:
    """Minimal scene graph that mirrors the bridge method surface."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._hip = "untitled.hip"
        self._nodes: dict[str, dict[str, Any]] = {
            "/obj": {
                "path": "/obj",
                "name": "obj",
                "type": "obj",
                "category": "Object",
                "parms": {},
                "children": [],
                "inputs": [],
                "outputs": [],
            }
        }
        self._docs = {
            "geo": {
                "id": "geo",
                "title": "Geometry Object",
                "text": "Container for SOP networks. Create under /obj.",
                "url": "houdini://docs/node/obj/geo",
                "metadata": {"category": "Object"},
            },
            "box": {
                "id": "box",
                "title": "Box SOP",
                "text": "Creates a polygonal or NURBS box. Common starter shape.",
                "url": "houdini://docs/node/sop/box",
                "metadata": {"category": "Sop"},
            },
            "null": {
                "id": "null",
                "title": "Null SOP",
                "text": "Pass-through node useful as an output or bookmark.",
                "url": "houdini://docs/node/sop/null",
                "metadata": {"category": "Sop"},
            },
        }

    def handle(self, method: str, params: dict[str, Any]) -> Any:
        handler = getattr(self, f"op_{method}", None)
        if handler is None:
            raise ValueError(f"unknown method: {method}")
        with self._lock:
            return handler(params)

    def op_ping(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "backend": "mock", "ts": time.time()}

    def op_get_scene_info(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {
            "hip_file": self._hip,
            "houdini_version": "mock-0.1",
            "fps": 24.0,
            "frame": 1.0,
            "node_count": len(self._nodes),
            "backend": "mock",
        }

    def op_list_nodes(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        parent = params.get("path") or "/obj"
        recursive = bool(params.get("recursive", False))
        if parent not in self._nodes:
            raise ValueError(f"node not found: {parent}")
        if not recursive:
            children = self._nodes[parent].get("children", [])
            return [copy.deepcopy(self._nodes[c]) for c in children]
        prefix = parent.rstrip("/") + "/"
        out = []
        for path, node in self._nodes.items():
            if path == parent or path.startswith(prefix):
                out.append(copy.deepcopy(node))
        return out

    def op_get_node(self, params: dict[str, Any]) -> dict[str, Any]:
        path = params["path"]
        if path not in self._nodes:
            raise ValueError(f"node not found: {path}")
        return copy.deepcopy(self._nodes[path])

    def op_create_node(self, params: dict[str, Any]) -> dict[str, Any]:
        parent = params["parent"]
        node_type = params["type"]
        name = params.get("name") or node_type
        if parent not in self._nodes:
            raise ValueError(f"parent not found: {parent}")
        path = f"{parent.rstrip('/')}/{name}"
        if path in self._nodes:
            raise ValueError(f"node already exists: {path}")
        node = {
            "path": path,
            "name": name,
            "type": node_type,
            "category": params.get("category") or "Sop",
            "parms": {},
            "children": [],
            "inputs": [],
            "outputs": [],
        }
        self._nodes[path] = node
        self._nodes[parent]["children"].append(path)
        return copy.deepcopy(node)

    def op_set_parm(self, params: dict[str, Any]) -> dict[str, Any]:
        path = params["path"]
        parm = params["parm"]
        value = params["value"]
        if path not in self._nodes:
            raise ValueError(f"node not found: {path}")
        self._nodes[path]["parms"][parm] = value
        return {"path": path, "parm": parm, "value": value}

    def op_connect_nodes(self, params: dict[str, Any]) -> dict[str, Any]:
        from_path = params["from_path"]
        to_path = params["to_path"]
        from_index = int(params.get("from_index", 0))
        to_index = int(params.get("to_index", 0))
        for path in (from_path, to_path):
            if path not in self._nodes:
                raise ValueError(f"node not found: {path}")
        self._nodes[to_path]["inputs"].append(
            {"from": from_path, "from_index": from_index, "to_index": to_index}
        )
        self._nodes[from_path]["outputs"].append(
            {"to": to_path, "from_index": from_index, "to_index": to_index}
        )
        return {
            "from_path": from_path,
            "to_path": to_path,
            "from_index": from_index,
            "to_index": to_index,
        }

    def op_delete_node(self, params: dict[str, Any]) -> dict[str, Any]:
        path = params["path"]
        if path in ("/obj", "/"):
            raise ValueError("refusing to delete root")
        if path not in self._nodes:
            raise ValueError(f"node not found: {path}")
        parent = path.rsplit("/", 1)[0] or "/"
        node = self._nodes.pop(path)
        if parent in self._nodes and path in self._nodes[parent]["children"]:
            self._nodes[parent]["children"].remove(path)
        # Drop descendants
        prefix = path + "/"
        for child in list(self._nodes):
            if child.startswith(prefix):
                del self._nodes[child]
        return {"deleted": path, "type": node["type"]}

    def op_execute_python(self, params: dict[str, Any]) -> dict[str, Any]:
        code = params.get("code") or ""
        # Mock evaluates nothing against hou; returns echo for safety.
        return {
            "stdout": "",
            "result": f"<mock executed {len(code)} chars>",
            "backend": "mock",
        }

    def op_save_hip(self, params: dict[str, Any]) -> dict[str, Any]:
        path = params.get("path") or self._hip
        self._hip = path
        return {"hip_file": path, "saved": True}

    def op_load_hip(self, params: dict[str, Any]) -> dict[str, Any]:
        path = params["path"]
        self._hip = path
        return {"hip_file": path, "loaded": True}

    def op_list_node_types(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        category = (params.get("category") or "").lower()
        items = []
        for doc in self._docs.values():
            cat = (doc.get("metadata") or {}).get("category", "")
            if category and cat.lower() != category.lower():
                continue
            items.append({"type": doc["id"], "label": doc["title"], "category": cat})
        return items

    def op_search(self, params: dict[str, Any]) -> dict[str, Any]:
        query = (params.get("query") or "").lower().strip()
        results = []
        for doc in self._docs.values():
            blob = f"{doc['id']} {doc['title']} {doc['text']}".lower()
            if not query or query in blob:
                results.append(
                    {"id": doc["id"], "title": doc["title"], "url": doc["url"]}
                )
        return {"results": results}

    def op_fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        doc_id = params["id"]
        if doc_id not in self._docs:
            raise ValueError(f"document not found: {doc_id}")
        return copy.deepcopy(self._docs[doc_id])
