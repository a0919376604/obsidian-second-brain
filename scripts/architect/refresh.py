"""Per-module refresh decision.

Pure decision function. Does not write files. Caller (scan.py or
slash command body) acts on the returned RefreshAction.
"""

from __future__ import annotations

import subprocess
from enum import Enum
from pathlib import Path


class RefreshAction(str, Enum):
    GENERATE = "generate"        # new module, no prior note
    REGENERATE = "regenerate"    # existing module changed
    SKIP = "skip"                # unchanged, only frontmatter touched


def decide_module_refresh(
    module: dict,
    lockfile_modules: dict,
    old_commit: str | None,
    new_commit: str,
    repo_root: Path,
    force: bool = False,
) -> RefreshAction:
    """Decide what to do with this module in the current refresh run.

    Args:
        module: current manifest module dict (slug, paths, ...).
        lockfile_modules: mapping {slug: {"paths": [...], ...}} from lockfile.
        old_commit: commit hash of last successful scan (None on first run).
        new_commit: commit hash of current scan.
        repo_root: repo path for git diff.
        force: --force flag bypasses skip logic.
    """
    slug = module["slug"]
    if slug not in lockfile_modules:
        return RefreshAction.GENERATE

    if force:
        return RefreshAction.REGENERATE

    old_paths = sorted(lockfile_modules[slug].get("paths", []))
    new_paths = sorted(module.get("paths", []))
    if old_paths != new_paths:
        return RefreshAction.REGENERATE

    if old_commit and new_commit and old_commit != new_commit:
        if _paths_changed_between_commits(repo_root, old_commit, new_commit, new_paths):
            return RefreshAction.REGENERATE

    return RefreshAction.SKIP


def _paths_changed_between_commits(
    repo_root: Path, old_commit: str, new_commit: str, paths: list[str]
) -> bool:
    """True iff git diff <old>..<new> -- <paths> reports any change."""
    cmd = ["git", "-C", str(repo_root), "diff", "--quiet", f"{old_commit}..{new_commit}", "--"] + paths
    result = subprocess.run(cmd, capture_output=True)
    # `git diff --quiet` exits 0 on no change, 1 on changes.
    return result.returncode == 1
