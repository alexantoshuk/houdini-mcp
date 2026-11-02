"""Autostart policy for the in-Houdini TCP bridge (no live Houdini required)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PY = ROOT / "houdini_plugin" / "python"
sys.path.insert(0, str(PLUGIN_PY))

import houdini_mcp_bridge as bridge  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("HOUDINI_MCP_NO_BRIDGE", raising=False)
    monkeypatch.delenv("HOUDINI_MCP_BRIDGE", raising=False)
    monkeypatch.setattr(bridge, "is_gui_session", lambda: False)


def test_hython_skips_autostart(monkeypatch):
    monkeypatch.setattr(bridge, "is_gui_session", lambda: False)
    ok, reason = bridge.should_autostart_bridge()
    assert ok is False
    assert "non-GUI" in reason


def test_gui_autostarts(monkeypatch):
    monkeypatch.setattr(bridge, "is_gui_session", lambda: True)
    ok, reason = bridge.should_autostart_bridge()
    assert ok is True
    assert reason == "gui session"


def test_no_bridge_env_wins(monkeypatch):
    monkeypatch.setenv("HOUDINI_MCP_NO_BRIDGE", "1")
    monkeypatch.setattr(bridge, "is_gui_session", lambda: True)
    ok, reason = bridge.should_autostart_bridge()
    assert ok is False
    assert "NO_BRIDGE" in reason


def test_force_bridge_in_hython(monkeypatch):
    monkeypatch.setenv("HOUDINI_MCP_BRIDGE", "1")
    monkeypatch.setattr(bridge, "is_gui_session", lambda: False)
    ok, reason = bridge.should_autostart_bridge()
    assert ok is True
    assert "HOUDINI_MCP_BRIDGE" in reason
