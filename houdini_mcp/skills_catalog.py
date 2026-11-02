"""Load houdini-* Agent Skills for MCP routing.

Primary source: public GitHub repo (raw.githubusercontent.com + Contents API).
Local `.cursor/skills/` is fallback only (offline / unpublished commits).

Env:
  HOUDINI_MCP_SKILLS_REPO   default alexantoshuk/houdini-mcp
  HOUDINI_MCP_SKILLS_REF    default main
  HOUDINI_MCP_SKILLS_SOURCE github | local | auto (default auto = github then local)
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILLS_ROOT = _REPO_ROOT / ".cursor" / "skills"

DEFAULT_REPO = "alexantoshuk/houdini-mcp"
DEFAULT_REF = "main"
_CACHE_TTL_S = 300.0
_UA = "houdini-mcp-skills/1.0"

# Topic → skill name hints for MCP instructions (not exhaustive).
ROUTING: list[tuple[str, str]] = [
    ("camera / framing / look-at / black beauty / HIP≠render / ракурс", "houdini-camera"),
    ("Solaris / LOPs / USD / Karma stage / husk export", "houdini-solaris"),
    ("render / ROP / AOVs / sampling / beauty", "houdini-render"),
    ("materials / lookdev / shade", "houdini-shade"),
    ("SOP modeling / geo / kitbash", "houdini-model"),
    ("VEX / wrangle", "houdini-vex"),
    ("debug / cook error / empty viewport", "houdini-troubleshooting"),
    ("any non-trivial Houdini task (start here)", "houdini-discipline"),
]

_cache: dict[str, Any] = {"list": None, "list_at": 0.0, "bodies": {}}


def skills_root() -> Path:
    return _SKILLS_ROOT


def _repo() -> str:
    return os.environ.get("HOUDINI_MCP_SKILLS_REPO", DEFAULT_REPO).strip() or DEFAULT_REPO


def _ref() -> str:
    return os.environ.get("HOUDINI_MCP_SKILLS_REF", DEFAULT_REF).strip() or DEFAULT_REF


def _source_mode() -> str:
    return (os.environ.get("HOUDINI_MCP_SKILLS_SOURCE") or "auto").strip().lower()


def _raw_url(skill_name: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{_repo()}/{_ref()}/"
        f".cursor/skills/{skill_name}/SKILL.md"
    )


def _api_list_url() -> str:
    return (
        f"https://api.github.com/repos/{_repo()}/contents/.cursor/skills"
        f"?ref={_ref()}"
    )


def _http_get(url: str, timeout: float = 12.0) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _UA,
            "Accept": "application/vnd.github+json, text/plain, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


def _parse_frontmatter(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    if not text.startswith("---"):
        return meta
    end = text.find("\n---", 3)
    if end < 0:
        return meta
    block = text[3:end]
    m = re.search(
        r"^description:\s*>-?\s*\n((?:[ \t]+.+\n?)+)",
        block,
        flags=re.MULTILINE,
    )
    if m:
        meta["description"] = " ".join(
            ln.strip() for ln in m.group(1).splitlines() if ln.strip()
        )
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip("\"'")
        if key == "name" and val:
            meta["name"] = val
        elif key == "description" and val and val not in {">-", ">"} and "description" not in meta:
            meta["description"] = val
    return meta


def _entry(name: str, description: str, *, source: str, url: str | None = None, path: str | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "source": source,
        "url": url,
        "path": path,
        "ref": _ref() if source == "github" else None,
        "repo": _repo() if source == "github" else None,
    }


def _list_local() -> list[dict[str, Any]]:
    root = skills_root()
    out: list[dict[str, Any]] = []
    if not root.is_dir():
        return out
    for skill_md in sorted(root.glob("houdini-*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        name = meta.get("name") or skill_md.parent.name
        out.append(
            _entry(
                name,
                meta.get("description", ""),
                source="local",
                path=str(skill_md).replace("\\", "/"),
            )
        )
    return out


def _list_github() -> list[dict[str, Any]]:
    raw = _http_get(_api_list_url())
    items = json.loads(raw.decode("utf-8"))
    if not isinstance(items, list):
        raise RuntimeError(f"unexpected GitHub API payload: {type(items)}")
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or item.get("type") != "dir":
            continue
        name = str(item.get("name") or "")
        if not name.startswith("houdini-"):
            continue
        # Prefer lightweight: description filled when get_skill is called, or fetch SKILL head
        url = _raw_url(name)
        desc = ""
        try:
            body = _http_get(url).decode("utf-8")
            desc = _parse_frontmatter(body).get("description", "")
            _cache["bodies"][name] = {"text": body, "at": time.time(), "url": url}
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        out.append(_entry(name, desc, source="github", url=url))
    out.sort(key=lambda s: s["name"])
    return out


def list_skills() -> list[dict[str, Any]]:
    mode = _source_mode()
    now = time.time()
    cached = _cache.get("list")
    if cached is not None and (now - float(_cache.get("list_at") or 0)) < _CACHE_TTL_S:
        return list(cached)

    errors: list[str] = []
    skills: list[dict[str, Any]] = []

    if mode in {"github", "auto"}:
        try:
            skills = _list_github()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"github: {exc}")

    if (not skills) and mode in {"local", "auto"}:
        skills = _list_local()
        if skills and errors:
            for s in skills:
                s["fallback_reason"] = "; ".join(errors)

    _cache["list"] = skills
    _cache["list_at"] = now
    return list(skills)


def _normalize_names(name: str) -> list[str]:
    key = name.strip()
    if key.startswith("houdini-"):
        return [key]
    return [f"houdini-{key}", key]


def get_skill(name: str) -> dict[str, Any]:
    """Return full SKILL.md body — GitHub first, then local fallback."""
    candidates = _normalize_names(name)
    mode = _source_mode()
    errors: list[str] = []

    if mode in {"github", "auto"}:
        for cand in candidates:
            url = _raw_url(cand)
            body_hit = _cache["bodies"].get(cand)
            if body_hit and (time.time() - float(body_hit["at"])) < _CACHE_TTL_S:
                text = body_hit["text"]
                meta = _parse_frontmatter(text)
                return {
                    "ok": True,
                    "name": meta.get("name") or cand,
                    "description": meta.get("description", ""),
                    "content": text,
                    "source": "github",
                    "url": url,
                    "repo": _repo(),
                    "ref": _ref(),
                }
            try:
                text = _http_get(url).decode("utf-8")
                _cache["bodies"][cand] = {"text": text, "at": time.time(), "url": url}
                meta = _parse_frontmatter(text)
                return {
                    "ok": True,
                    "name": meta.get("name") or cand,
                    "description": meta.get("description", ""),
                    "content": text,
                    "source": "github",
                    "url": url,
                    "repo": _repo(),
                    "ref": _ref(),
                }
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    errors.append(f"{cand} github HTTP {exc.code}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{cand} github: {exc}")

    if mode in {"local", "auto"}:
        by_name = {s["name"]: s for s in _list_local()}
        for cand in candidates:
            if cand in by_name:
                path = Path(by_name[cand]["path"])
                text = path.read_text(encoding="utf-8")
                return {
                    "ok": True,
                    "name": by_name[cand]["name"],
                    "description": by_name[cand].get("description", ""),
                    "content": text,
                    "source": "local",
                    "path": by_name[cand]["path"],
                    "fallback_reason": "; ".join(errors) if errors else None,
                }

    available = [s["name"] for s in list_skills()]
    return {
        "ok": False,
        "error": f"unknown skill {name!r}",
        "available": available,
        "tried": errors,
        "repo": _repo(),
        "ref": _ref(),
    }


def instructions_skill_section() -> str:
    lines = [
        "Workflow skills: when the user task matches a topic below, call get_skill",
        "with that name and follow the returned SKILL.md before changing the scene.",
        f"Skills load from public GitHub {_repo()}@{_ref()} "
        "(.cursor/skills/.../SKILL.md); local clone is offline fallback only.",
        "",
        "Routing:",
    ]
    for topic, skill in ROUTING:
        lines.append(f"- {topic} → get_skill('{skill}')")
    lines.append("- list_skills() to see the full catalog.")
    return "\n".join(lines)


def clear_cache() -> None:
    _cache["list"] = None
    _cache["list_at"] = 0.0
    _cache["bodies"] = {}
