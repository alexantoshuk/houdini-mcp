# Agent rules — houdini-mcp

Rules for any agent working in this repository and driving SideFX Houdini via MCP.

## HIP save discipline (mandatory)

Losing a session to a crash or a hung Karma/husk job is expected risk. Protect the user’s work:

1. **Before starting scene work** — save the hip to a path **outside this repo** (see below). If the session is still `untitled.hip`, save-as immediately.
2. **During work** — save periodically after meaningful milestones (network built, materials assigned, lights placed, before big caches).
3. **Before every render** — save the hip again, then start the render / husk job.
4. Prefer `save_hip` (MCP) or equivalent; confirm the path with the user when ambiguous.

## Do not store scene work in this repo

This repository is the **MCP server + Zed extension + skills**. It is not a shot/project archive.

**Keep out of `houdini-mcp`:**

- `.hip` / `.hipnc` scene files
- Renders (`*.exr`, `*.png`, playblasts, husk logs)
- Exported USD/Alembic/caches for a specific brief
- One-off “build this kitchen / this shot” Python scripts
- Scratch probes, `_export_*.py`, `fix_*_render.py`, etc.

**Put that work elsewhere**, for example:

- `Documents/houdini_work/<shot_or_client>/`
- Or another folder the user names

If you need a temporary script to drive the live session, write it under that external work folder (or `%TEMP%`), run it via the bridge, and do **not** commit it here.

Reusable product code (bridge, MCP tools, installers, skill importers) stays in this repo.

## Where skills live

| Location | Role |
| --- | --- |
| `.cursor/skills/houdini-*/SKILL.md` | Cursor project skills — **primary** source agents should load |
| `skills/README.md` | Index of skill names / topics |
| `skills/SECURITY.md` | Security review notes for imported guides |
| `skills/vendor/fxhoudinimcp/` | Upstream raw workflow markdown (MIT attribution) |
| `skills/ATTRIBUTION.md` | License / source credit |

Start from **`houdini-discipline`** for any non-trivial Houdini task, then the topic skill (`houdini-solaris`, `houdini-model`, `houdini-vex`, …).

Re-import / regenerate Cursor skills: `python scripts/import_fxhoudini_skills.py`  
Security scan: `python scripts/scan_skills_security.py`

## Keep skills alive (avoid repeating mistakes)

Skills are living docs for this project:

- When a workflow fails and you learn the fix (wrong LOP type name, Camera `_control` must be Set, Karma parms locked, bridge autostart path, render hung the MCP main thread, …), **update the relevant `SKILL.md`** (or add a short note under that skill) so the next session does not repeat it.
- When the user corrects a preference or a studio convention, capture it in the matching skill or in this `AGENTS.md` if it is global.
- Prefer small, concrete additions (pitfall + correct approach) over rewriting whole guides.
- After skill edits that should ship with the repo, commit them with the related change — do not leave hard-won fixes only in chat history.

## Quick MCP reminders

- Live bridge: `127.0.0.1:18812` (Houdini package / user `scripts/456.py`).
- Prefer typed tools; use `execute_python` only when necessary and never for host shell / network / secrets.
- External / farm submits and long caches need explicit user confirmation.
