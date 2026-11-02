"""Backend selector: mock in-process scene or live TCP bridge to Houdini."""

from __future__ import annotations

import os
import threading
from typing import Any, Protocol

from .bridge_client import BridgeClient, BridgeError
from .mock_backend import MockHoudiniBackend


class Backend(Protocol):
    def call(self, method: str, params: dict[str, Any] | None = None) -> Any: ...


class MockBackendAdapter:
    def __init__(self) -> None:
        self._backend = MockHoudiniBackend()

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        try:
            return self._backend.handle(method, params or {})
        except Exception as exc:  # noqa: BLE001 — surface as tool error
            raise BridgeError(str(exc), "mock_error") from exc


class LiveBackendAdapter:
    def __init__(self) -> None:
        self._client = BridgeClient()

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        return self._client.call(method, params)


_lock = threading.Lock()
_backend: Backend | None = None


def use_mock() -> bool:
    flag = os.environ.get("HOUDINI_MCP_MOCK", "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def get_backend() -> Backend:
    global _backend
    with _lock:
        if _backend is None:
            _backend = MockBackendAdapter() if use_mock() else LiveBackendAdapter()
        return _backend


def reset_backend() -> None:
    global _backend
    with _lock:
        _backend = None
