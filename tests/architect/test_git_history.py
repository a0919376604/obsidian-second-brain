"""Tests for scripts.architect.git_history.last_touch_map."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.architect.git_history import last_touch_map


def _init_git_repo(repo: Path):
    """Initialize a git repo with a known config so commits succeed in CI."""
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)


def _commit(repo: Path, path: str, content: str, date: str):
    file_path = repo / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", path], cwd=repo, check=True)
    env = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    subprocess.run(
        ["git", "commit", "-m", f"add {path}", "--date", date],
        cwd=repo,
        check=True,
        capture_output=True,
        env={**__import__("os").environ, **env},
    )


def test_returns_last_touch_dates_for_committed_files(tmp_path):
    _init_git_repo(tmp_path)
    _commit(tmp_path, "a.py", "x=1\n", "2026-05-01T12:00:00")
    _commit(tmp_path, "b.py", "y=2\n", "2025-09-12T08:30:00")
    result = last_touch_map(tmp_path, ["a.py", "b.py"])
    assert result["a.py"] == "2026-05-01"
    assert result["b.py"] == "2025-09-12"


def test_omits_uncommitted_files(tmp_path):
    """Files never committed → key absent (not '—', not 'unknown')."""
    _init_git_repo(tmp_path)
    _commit(tmp_path, "tracked.py", "z=3\n", "2026-04-01T00:00:00")
    (tmp_path / "untracked.py").write_text("u=1\n", encoding="utf-8")
    result = last_touch_map(tmp_path, ["tracked.py", "untracked.py"])
    assert result["tracked.py"] == "2026-04-01"
    assert "untracked.py" not in result
