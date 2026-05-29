"""Resolve a CLI `<repo>` argument into a vault project binding.

Used by the obsidian-* command family (architect / brainstorm / roadmap /
research / research-deep). Accepts three forms:
- Sentinel ('global' / '_' / '-') -> state='global' (research commands only)
- Absolute path -> match against project hub `local-path` frontmatter
- Project name -> exact match against Projects/<name>/ folder, then fuzzy

Caller branches on `RepoResolution.state` to either continue execution,
ask the user to disambiguate, or abort with a message.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path


_GLOBAL_SENTINELS = ("global", "_", "-")


@dataclass
class RepoResolution:
    state: str
    project_slug: str | None = None
    project_dir: Path | None = None
    local_path: str | None = None
    candidates: list[str] = field(default_factory=list)
    message: str = ""


def resolve_repo_arg(
    token: str,
    vault_root: Path,
    *,
    allow_global: bool = False,
) -> RepoResolution:
    """Resolve a `<repo>` CLI token. See module docstring for full spec."""
    token = token.strip()
    if not token:
        return RepoResolution(
            state="unknown",
            candidates=[],
            message="missing <repo> argument",
        )

    if token in _GLOBAL_SENTINELS:
        if allow_global:
            return RepoResolution(state="global")
        return RepoResolution(
            state="unknown",
            candidates=_list_projects(vault_root),
            message=(
                "'global' sentinel is not allowed for this command. "
                "Pass a specific project name."
            ),
        )

    if token.startswith("/"):
        return _resolve_absolute_path(token, vault_root)

    return _resolve_project_name(token, vault_root)


def _list_projects(vault_root: Path) -> list[str]:
    projects_dir = vault_root / "Projects"
    if not projects_dir.is_dir():
        return []
    return sorted(
        d.name
        for d in projects_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_")
    )


def _resolve_absolute_path(token: str, vault_root: Path) -> RepoResolution:
    """Placeholder filled in by Task 2."""
    return RepoResolution(
        state="unknown",
        candidates=_list_projects(vault_root),
        message=f"absolute-path resolution not yet implemented for token: {token}",
    )


def _resolve_project_name(token: str, vault_root: Path) -> RepoResolution:
    """Project-name branch: exact match first."""
    projects_dir = vault_root / "Projects"
    if not projects_dir.is_dir():
        return RepoResolution(
            state="unknown",
            candidates=[],
            message="vault has no Projects/ folder",
        )
    exact = projects_dir / token
    if exact.is_dir():
        return RepoResolution(
            state="project",
            project_slug=token,
            project_dir=exact,
        )
    return RepoResolution(
        state="unknown",
        candidates=_list_projects(vault_root),
        message=f"no project named {token!r}; available: {_list_projects(vault_root)}",
    )
