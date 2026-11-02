"""TCP JSON-lines client talking to the in-Houdini bridge (or mock)."""

from __future__ import annotations

import json
import os
import socket
import time
import uuid
from typing import Any

from .protocol import DEFAULT_HOST, DEFAULT_PORT, make_request


class BridgeError(RuntimeError):
    def __init__(self, message: str, code: str = "bridge_error") -> None:
        super().__init__(message)
        self.code = code


class BridgeClient:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.host = host or os.environ.get("HOUDINI_MCP_HOST", DEFAULT_HOST)
        self.port = int(port or os.environ.get("HOUDINI_MCP_PORT", DEFAULT_PORT))
        self.timeout = timeout

    def ping(self) -> dict[str, Any]:
        return self.call("ping")

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        req_id = str(uuid.uuid4())
        payload = make_request(req_id, method, params)
        raw = self._exchange(payload)
        if not raw.get("ok", False):
            err = raw.get("error") or {}
            if isinstance(err, dict):
                raise BridgeError(err.get("message", "unknown bridge error"), err.get("code", "error"))
            raise BridgeError(str(err))
        return raw.get("result")

    def _exchange(self, payload: dict[str, Any]) -> dict[str, Any]:
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            sock.sendall(line.encode("utf-8"))
            data = b""
            while b"\n" not in data:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
        if not data:
            raise BridgeError("empty response from Houdini bridge", "empty_response")
        try:
            return json.loads(data.decode("utf-8").splitlines()[0])
        except json.JSONDecodeError as exc:
            raise BridgeError(f"invalid JSON from bridge: {exc}", "bad_json") from exc

    def wait_until_ready(self, attempts: int = 20, delay: float = 0.25) -> bool:
        for _ in range(attempts):
            try:
                self.ping()
                return True
            except OSError:
                time.sleep(delay)
            except BridgeError:
                time.sleep(delay)
        return False
