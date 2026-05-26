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

import json

from scripts.architect.walker import walk_repo


def propose_modules_with_heuristics(repo_root: Path) -> list[dict]:
    """Run the full proposal pipeline: default + monorepo + flat + merge/split."""
    repo_root = repo_root.resolve()

    # 1. Monorepo detection short-circuits the rest.
    workspaces = _detect_workspaces(repo_root)
    if workspaces:
        return _monorepo_proposal(repo_root, workspaces)

    # 2. Start with default.
    modules = propose_modules(repo_root)

    # 3. Flat-repo fallback.
    non_skip = [m for m in modules if not m["excluded"]]
    if len(non_skip) < 3:
        modules = _flat_repo_proposal(repo_root, modules)

    return modules


def _detect_workspaces(repo_root: Path) -> list[str]:
    """Detect monorepo workspaces from pnpm/yarn/npm/cargo/go config.

    Returns the list of workspace member directory paths (relative).
    Empty list means not a monorepo.
    """
    # pnpm
    pnpm = repo_root / "pnpm-workspace.yaml"
    if pnpm.exists():
        import yaml
        data = yaml.safe_load(pnpm.read_text()) or {}
        patterns = data.get("packages", [])
        return _expand_workspace_globs(repo_root, patterns)

    # npm/yarn workspaces in package.json
    pkg = repo_root / "package.json"
    if pkg.exists():
        data = json.loads(pkg.read_text())
        ws = data.get("workspaces")
        if isinstance(ws, list):
            return _expand_workspace_globs(repo_root, ws)
        if isinstance(ws, dict) and "packages" in ws:
            return _expand_workspace_globs(repo_root, ws["packages"])

    # Cargo workspace
    cargo = repo_root / "Cargo.toml"
    if cargo.exists():
        try:
            import tomllib  # type: ignore[import-not-found]
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(cargo.read_text())
        members = data.get("workspace", {}).get("members", [])
        return _expand_workspace_globs(repo_root, members)

    return []


def _expand_workspace_globs(repo_root: Path, patterns: list[str]) -> list[str]:
    """Expand patterns like 'packages/*' into concrete relative directory paths."""
    import fnmatch

    out: list[str] = []
    for pattern in patterns:
        if "*" in pattern:
            base = pattern.split("*")[0].rstrip("/")
            base_path = repo_root / base
            if base_path.is_dir():
                for sub in sorted(base_path.iterdir()):
                    if sub.is_dir() and fnmatch.fnmatch(sub.name, pattern.split("/")[-1]):
                        out.append(sub.relative_to(repo_root).as_posix())
        else:
            full = repo_root / pattern
            if full.is_dir():
                out.append(pattern)
    return out


def _monorepo_proposal(repo_root: Path, workspaces: list[str]) -> list[dict]:
    modules: list[dict] = []
    for ws_path in workspaces:
        slug = _slugify(Path(ws_path).name)
        modules.append({
            "slug": slug,
            "display_name": Path(ws_path).name.replace("-", " ").replace("_", " ").title(),
            "paths": [ws_path + "/"],
            "role": "other",
            "excluded": False,
            "description": None,
            "pattern": None,
        })
    return modules


def _flat_repo_proposal(repo_root: Path, base: list[dict]) -> list[dict]:
    """Add a 'core' module covering the repo root files, alongside any folders."""
    # Keep non-skip folder modules; prepend a 'core' module for root-level files.
    folder_modules = base
    core = {
        "slug": "core",
        "display_name": "Core",
        "paths": ["./"],
        "role": "core",
        "excluded": False,
        "description": None,
        "pattern": None,
    }
    return [core] + folder_modules
