"""Tests for scripts.commands.repo_resolver.resolve_repo_arg."""
from __future__ import annotations

from pathlib import Path

from scripts.commands.repo_resolver import RepoResolution, resolve_repo_arg


def _make_vault(tmp_path: Path, project_names: list[str]) -> Path:
    """Build a minimal vault with given project folders + each has a hub note."""
    (tmp_path / "_CLAUDE.md").write_text("vault root marker\n", encoding="utf-8")
    projects = tmp_path / "Projects"
    projects.mkdir()
    for name in project_names:
        proj_dir = projects / name
        proj_dir.mkdir()
        (proj_dir / f"{name}.md").write_text(
            "---\n"
            "type: project\n"
            f'project: "[[{name}]]"\n'
            "---\n",
            encoding="utf-8",
        )
    return tmp_path


def test_resolve_repo_arg_exact_project_name(tmp_path: Path):
    """Token matches a Projects/<name>/ folder exactly -> state='project', bind."""
    vault = _make_vault(tmp_path, ["langlive-line-oa", "ai-eden-service"])
    res = resolve_repo_arg("langlive-line-oa", vault_root=vault, allow_global=False)
    assert res.state == "project"
    assert res.project_slug == "langlive-line-oa"
    assert res.project_dir == vault / "Projects/langlive-line-oa"


def test_resolve_repo_arg_global_sentinel_when_allowed(tmp_path: Path):
    """Token 'global' with allow_global=True -> state='global'."""
    vault = _make_vault(tmp_path, ["whatever"])
    res = resolve_repo_arg("global", vault_root=vault, allow_global=True)
    assert res.state == "global"
    assert res.project_slug is None
    assert res.project_dir is None


def test_resolve_repo_arg_underscore_and_dash_also_global(tmp_path: Path):
    """Aliases '_' and '-' are also global sentinels when allowed."""
    vault = _make_vault(tmp_path, ["whatever"])
    assert resolve_repo_arg("_", vault_root=vault, allow_global=True).state == "global"
    assert resolve_repo_arg("-", vault_root=vault, allow_global=True).state == "global"


def test_resolve_repo_arg_global_rejected_when_not_allowed(tmp_path: Path):
    """Token 'global' with allow_global=False -> state='unknown'."""
    vault = _make_vault(tmp_path, ["whatever"])
    res = resolve_repo_arg("global", vault_root=vault, allow_global=False)
    assert res.state == "unknown"
    assert "global" in res.message.lower() or "not allowed" in res.message.lower()
