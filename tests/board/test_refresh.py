"""Tests for scripts.board.refresh.refresh_board."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from scripts.board.refresh import RefreshResult, refresh_board


def test_refresh_returns_skipped_when_no_board_md(tmp_path: Path):
    """When Projects/<P>/board.md doesn't exist -> status='skipped'."""
    proj_dir = tmp_path / "Projects" / "myproject"
    proj_dir.mkdir(parents=True)
    # No board.md exists -- only hub note.
    (proj_dir / "myproject.md").write_text(
        "---\nlocal-path: /tmp/myrepo\n---\n", encoding="utf-8"
    )

    result = refresh_board(project_dir=proj_dir, signals=None, full=False)
    assert isinstance(result, RefreshResult)
    assert result.status == "skipped"
    assert "no board.md" in result.message.lower()
    assert result.project_slug == "myproject"


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)


def _commit(repo: Path, path: str, content: str, message: str, date: str) -> None:
    p = repo / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", path], cwd=repo, check=True)
    env = {**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    subprocess.run(
        ["git", "commit", "-m", message, "--date", date],
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )


def test_refresh_walks_git_log_when_signals_none(tmp_path: Path):
    """signals=None -> helper walks git log itself; populates new_items."""
    # Project skeleton.
    proj_dir = tmp_path / "Projects" / "myproject"
    proj_dir.mkdir(parents=True)
    (proj_dir / "myproject.md").write_text(
        f"---\nlocal-path: {tmp_path / 'repo'}\n---\n", encoding="utf-8"
    )
    (proj_dir / "board.md").write_text(
        "---\nlast-refresh: 2026-05-01T00:00:00\n---\n\n"
        "## 待辦\n- placeholder\n",
        encoding="utf-8",
    )

    # Repo with one commit AFTER last-refresh.
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _commit(repo, "a.py", "x=1\n", "add a", "2026-05-15T12:00:00")

    result = refresh_board(project_dir=proj_dir, signals=None, full=False)
    assert result.status == "ok"
    assert result.last_refresh_before == "2026-05-01T00:00:00"
    titles = [item.get("title", "") for item in result.new_items]
    assert any("add a" in t for t in titles), f"expected commit picked up; got {titles}"


def test_refresh_full_mode_ignores_last_refresh(tmp_path: Path):
    """full=True walks ALL git history regardless of last-refresh timestamp."""
    proj_dir = tmp_path / "Projects" / "myproject"
    proj_dir.mkdir(parents=True)
    (proj_dir / "myproject.md").write_text(
        f"---\nlocal-path: {tmp_path / 'repo'}\n---\n", encoding="utf-8"
    )
    (proj_dir / "board.md").write_text(
        "---\nlast-refresh: 2030-01-01T00:00:00\n---\n",
        encoding="utf-8",
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _commit(repo, "a.py", "x=1\n", "old commit", "2026-01-01T00:00:00")

    # Without full=True the future timestamp would exclude everything.
    result = refresh_board(project_dir=proj_dir, signals=None, full=True)
    assert result.status == "ok"
    titles = [item.get("title", "") for item in result.new_items]
    assert any("old commit" in t for t in titles), (
        f"full mode should include pre-last-refresh commits; got {titles}"
    )
