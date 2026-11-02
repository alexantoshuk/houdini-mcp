"""Static security scan of imported Houdini skills."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".cursor" / "skills"
VENDOR = ROOT / "skills" / "vendor"

PATTERNS = {
    "prompt_injection": re.compile(
        r"ignore (previous|all|above)|disregard (your|system)|jailbreak|"
        r"developer mode|do not (tell|reveal)|system prompt",
        re.I,
    ),
    "secrets": re.compile(
        r"api[_-]?key|password|secret|credential|bearer |private[_-]?key",
        re.I,
    ),
    "shell_exfil": re.compile(
        r"\b(curl|wget|Invoke-WebRequest|powershell\s+-|cmd\.exe|bash\s+-c|"
        r"nc\s+|ncat|scp\s+|ftp\s+)\b",
        re.I,
    ),
    "code_exec_host": re.compile(
        r"\b(os\.system|subprocess\.|eval\(|exec\(|__import__|ctypes\.|"
        r"pickle\.loads|marshal\.loads)\b",
        re.I,
    ),
    "destructive_fs": re.compile(
        r"\b(rm\s+-rf|Remove-Item\s+-Recurse|shutil\.rmtree|format\s+c:|"
        r"del\s+/[sqf])\b",
        re.I,
    ),
    "network_exfil": re.compile(
        r"\b(webhook|ngrok|pastebin|discord\.com/api|telegram\.org)\b",
        re.I,
    ),
    "hidden_unicode": re.compile(r"[\u200b\u200c\u200d\ufeff\u202a-\u202e]"),
    "html_script": re.compile(r"<!--|<script|javascript:", re.I),
    "farm_remote": re.compile(
        r"\b(tractor|deadline|hqueue|farm|sendcommand|servicestart|"
        r"run_shelf_tool|execute_python)\b",
        re.I,
    ),
    "write_disk": re.compile(
        r"\b(write_cache|start_render|save_hip|hipFile\.save|filecache|"
        r"background=True)\b",
        re.I,
    ),
}


def scan(path: Path) -> dict[str, list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    hits: dict[str, list[str]] = {}
    for name, rx in PATTERNS.items():
        found = []
        for m in rx.finditer(text):
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            snippet = text[start:end].replace("\n", " ")
            found.append(snippet)
        if found:
            hits[name] = found[:8]
    return hits


def main() -> None:
    files = list(SKILLS.glob("*/SKILL.md")) + list(VENDOR.rglob("*.md"))
    summary: dict[str, int] = {k: 0 for k in PATTERNS}
    risky_files = []
    for path in sorted(files):
        hits = scan(path)
        if not hits:
            continue
        # Ignore attribution-only github links etc. by filtering categories
        notable = {
            k: v
            for k, v in hits.items()
            if k
            not in {
                # informational categories counted separately
            }
        }
        for k, v in hits.items():
            summary[k] += len(v)
        # High concern categories
        high = {
            k: v
            for k, v in hits.items()
            if k
            in {
                "prompt_injection",
                "secrets",
                "shell_exfil",
                "code_exec_host",
                "destructive_fs",
                "network_exfil",
                "hidden_unicode",
                "html_script",
            }
        }
        if high:
            risky_files.append((path, high))
        elif "farm_remote" in hits or "write_disk" in hits:
            # expected operational risk — report aggregate only
            pass

    print("=== AGGREGATE MATCH COUNTS ===")
    for k, n in summary.items():
        print(f"{k:20} {n}")

    print("\n=== HIGH-CONCERN FILE HITS ===")
    if not risky_files:
        print("none")
    for path, high in risky_files:
        print(f"\n{path.relative_to(ROOT)}")
        for k, snippets in high.items():
            print(f"  [{k}]")
            for s in snippets[:3]:
                print(f"    ...{s}...")

    # Size report
    print("\n=== LARGEST SKILLS ===")
    sizes = sorted(
        ((p.stat().st_size, p) for p in SKILLS.glob("*/SKILL.md")), reverse=True
    )
    for sz, p in sizes[:5]:
        print(f"{sz:7}  {p.parent.name}")


if __name__ == "__main__":
    main()
