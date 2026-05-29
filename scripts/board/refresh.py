"""Refresh Projects/<P>/board.md via deterministic git + spec/plan walk.

Shared helper for two callers:
- `/obsidian-board --refresh` (cron path) - passes signals=None; helper walks
  git log + spec/plan files itself.
- `/obsidian-architect` Phase 7 - passes signals dict with already-collected
  `git_last_touch`, git_log, spec/plan lists; helper reuses to avoid re-walking.

Bucket clustering is keyword-overlap match against existing bucket H2 headings
in the current board.md. Unmatched items go to `## Misc / Untriaged`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RefreshResult:
    status: str
    project_slug: str = ""
    board_path: Path | None = None
    done_count: int = 0
    in_flight_count: int = 0
    backlog_count: int = 0
    buckets: list[str] = field(default_factory=list)
    new_items: list[dict] = field(default_factory=list)
    last_refresh_before: str | None = None
    last_refresh_after: str = ""
    message: str = ""


def refresh_board(
    project_dir: Path,
    *,
    signals: dict | None = None,
    full: bool = False,
) -> RefreshResult:
    """Refresh board.md for the given project.

    See module docstring for the contract.
    """
    project_slug = project_dir.name
    board_path = project_dir / "board.md"
    if not board_path.is_file():
        return RefreshResult(
            status="skipped",
            project_slug=project_slug,
            board_path=board_path,
            message=f"no board.md in {project_slug} - run /obsidian-project to bootstrap",
        )

    # Full implementation lands in subsequent tasks. For now, return ok with
    # a stub message so the skipped path can be tested independently.
    return RefreshResult(
        status="ok",
        project_slug=project_slug,
        board_path=board_path,
        message="not yet implemented",
    )
