"""Module proposal heuristics.

Inputs: repo path. Output: list of proposed module dicts ready for
inclusion in _manifest.yml. Pure function, no I/O beyond reading the
repo filesystem.

Module dict shape:
    {"slug": str, "display_name": str, "paths": [str], "role": str,
     "excluded": bool, "description": None, "pattern": None}
"""

from __future__ import annotations

import re
from pathlib import Path

# Folders that become modules with excluded=True. They show up in
# overview narrative but no per-module note is generated.
SKIP_AS_MODULE = {
    "tests", "test", "__tests__", "spec",
    "docs", "documentation",
    "examples", "example",
    ".github",
    "dist", "build", "target", "out",
}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    s = _SLUG_RE.sub("-", name.lower()).strip("-")
    return s or "module"


def _candidate_roots(repo_root: Path) -> list[Path]:
    """Where to look for top-level modules.

    If src/ exists and contains folders, that's the module root.
    Otherwise the repo root itself.
    """
    src = repo_root / "src"
    if src.is_dir() and any(p.is_dir() for p in src.iterdir()):
        return [src]
    return [repo_root]


def propose_modules(repo_root: Path) -> list[dict]:
    """Default proposal: one module per first-level folder under the module root."""
    repo_root = repo_root.resolve()
    roots = _candidate_roots(repo_root)
    modules: list[dict] = []
    seen: set[str] = set()

    for root in roots:
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("."):
                continue
            slug = _slugify(entry.name)
            if slug in seen:
                continue
            seen.add(slug)
            rel_path = entry.relative_to(repo_root).as_posix() + "/"
            modules.append({
                "slug": slug,
                "display_name": entry.name.replace("-", " ").replace("_", " ").title(),
                "paths": [rel_path],
                "role": "other",
                "excluded": entry.name in SKIP_AS_MODULE,
                "description": None,
                "pattern": None,
            })
    return modules
