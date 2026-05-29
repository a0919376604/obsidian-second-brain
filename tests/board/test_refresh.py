"""Tests for scripts.board.refresh.refresh_board."""
from __future__ import annotations

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
