"""Skill catalog: GitHub primary + local fallback."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from houdini_mcp import skills_catalog as sc


@pytest.fixture(autouse=True)
def _local_mode(monkeypatch):
    monkeypatch.setenv("HOUDINI_MCP_SKILLS_SOURCE", "local")
    sc.clear_cache()
    yield
    sc.clear_cache()


def test_list_skills_includes_camera_and_discipline():
    names = {s["name"] for s in sc.list_skills()}
    assert "houdini-camera" in names
    assert "houdini-discipline" in names
    assert "houdini-solaris" in names


def test_get_skill_camera_body():
    payload = sc.get_skill("houdini-camera")
    assert payload["ok"] is True
    assert payload["source"] == "local"
    assert "look-at" in payload["content"].lower() or "Look-at" in payload["content"]
    assert payload["name"] == "houdini-camera"


def test_get_skill_short_name():
    payload = sc.get_skill("camera")
    assert payload["ok"] is True
    assert payload["name"] == "houdini-camera"


def test_instructions_mention_github_and_get_skill():
    text = sc.instructions_skill_section()
    assert "get_skill('houdini-camera')" in text
    assert "list_skills()" in text
    assert "alexantoshuk/houdini-mcp" in text


def test_raw_url_shape():
    assert sc._raw_url("houdini-camera").endswith(
        "/.cursor/skills/houdini-camera/SKILL.md"
    )
