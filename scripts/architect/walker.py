"""Repo file walker. Filesystem traversal with .gitignore handling.

This module knows about files and directories. It does not know about
modules, manifests, or anything domain-specific to /obsidian-architect.
"""

from __future__ import annotations

from pathlib import Path

import pathspec

# Always-skip prefixes regardless of .gitignore. Includes .git itself
# (which is never gitignored but must not be walked) plus build outputs
# and dependency caches that are by convention not part of source.
ALWAYS_SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    "out",
    ".next",
}


def _load_gitignore(repo_root: Path) -> pathspec.PathSpec:
    """Load .gitignore patterns from the repo root, if present."""
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])
    with gitignore.open() as fh:
        return pathspec.PathSpec.from_lines("gitwildmatch", fh)


def _is_binary(path: Path) -> bool:
    """Cheap binary detection: scan first 8KB for a NUL byte."""
    try:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return True
    return b"\x00" in chunk


def walk_repo(repo_root: Path) -> list[str]:
    """Return a sorted list of POSIX-style relative file paths.

    Excludes: .git/, conventional build/cache dirs, .gitignore matches,
    binary files. Symlinks are followed only if they resolve inside repo_root.
    """
    repo_root = repo_root.resolve()
    spec = _load_gitignore(repo_root)
    results: list[str] = []

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue

        # Always-skip check (by any path part)
        if any(part in ALWAYS_SKIP_DIRS for part in path.relative_to(repo_root).parts):
            continue

        rel = path.relative_to(repo_root).as_posix()
        if spec.match_file(rel):
            continue

        if _is_binary(path):
            continue

        # Symlink safety: must resolve inside repo_root.
        try:
            resolved = path.resolve()
            resolved.relative_to(repo_root)
        except ValueError:
            continue

        results.append(rel)

    return sorted(results)
