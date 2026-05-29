"""Refresh Projects/<P>/board.md via deterministic git + spec/plan walk."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


_FRONTMATTER_LAST_REFRESH_RE = re.compile(
    r'^last-refresh:\s*"?(?P<ts>[^"\n]+)"?\s*$', re.MULTILINE
)
_FRONTMATTER_LOCAL_PATH_RE = re.compile(
    r'^local-path:\s*"?(?P<path>[^"\n]+)"?\s*$', re.MULTILINE
)


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
    project_slug = project_dir.name
    board_path = project_dir / "board.md"
    if not board_path.is_file():
        return RefreshResult(
            status="skipped",
            project_slug=project_slug,
            board_path=board_path,
            message=f"no board.md in {project_slug} - run /obsidian-project to bootstrap",
        )

    board_text = board_path.read_text(encoding="utf-8")
    last_refresh_before = _read_last_refresh(board_text)
    local_path = _resolve_local_path(project_dir, project_slug)

    if signals is None:
        since = None if full else last_refresh_before
        new_items = _walk_signals(local_path, since=since) if local_path else []
    else:
        new_items = _new_items_from_signals(signals)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    return RefreshResult(
        status="ok",
        project_slug=project_slug,
        board_path=board_path,
        new_items=new_items,
        last_refresh_before=last_refresh_before,
        last_refresh_after=now_iso,
        message=f"walked {len(new_items)} items",
    )


def _read_last_refresh(text: str) -> str | None:
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    fm = m.group(1)
    sm = _FRONTMATTER_LAST_REFRESH_RE.search(fm)
    return sm.group("ts").strip() if sm else None


def _resolve_local_path(project_dir: Path, project_slug: str) -> Path | None:
    hub_path = project_dir / f"{project_slug}.md"
    if not hub_path.is_file():
        return None
    text = hub_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    fm = m.group(1)
    sm = _FRONTMATTER_LOCAL_PATH_RE.search(fm)
    if not sm:
        return None
    return Path(sm.group("path").strip())


def _walk_signals(local_path: Path, *, since: str | None) -> list[dict]:
    """Walk git log + spec/plan files. Each entry: {title, kind, when, source}."""
    if not local_path or not local_path.exists():
        return []
    items: list[dict] = []
    items.extend(_git_log_items(local_path, since=since))
    items.extend(_spec_plan_items(local_path, since=since))
    return items


def _git_log_items(repo: Path, *, since: str | None) -> list[dict]:
    cmd = [
        "git",
        "log",
        "--all",
        "--pretty=format:%H%x09%ad%x09%s%x09%D",
        "--date=iso-strict",
    ]
    if since:
        cmd.append(f"--since={since}")
    try:
        proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, check=False)
    except (FileNotFoundError, OSError):
        return []
    if proc.returncode != 0:
        return []
    items: list[dict] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        sha, when, subject = parts[0], parts[1], parts[2]
        refs = parts[3] if len(parts) > 3 else ""
        items.append(
            {
                "title": subject,
                "kind": "commit",
                "when": when,
                "source": f"commit {sha[:8]}",
                "refs": refs,
            }
        )
    return items


def _spec_plan_items(repo: Path, *, since: str | None) -> list[dict]:
    """List spec/plan files under docs/superpowers/. Filter by mtime if since set."""
    docs = repo / "docs" / "superpowers"
    if not docs.is_dir():
        return []
    items: list[dict] = []
    cutoff = _parse_iso_ts(since) if since else None
    for sub in ("specs", "plans"):
        d = docs / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            mtime = f.stat().st_mtime
            if cutoff is not None and mtime < cutoff:
                continue
            items.append(
                {
                    "title": f.stem,
                    "kind": sub.rstrip("s"),
                    "when": datetime.fromtimestamp(mtime).isoformat(),
                    "source": f.relative_to(repo).as_posix(),
                }
            )
    return items


def _parse_iso_ts(ts: str) -> float | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


def _new_items_from_signals(signals: dict) -> list[dict]:
    """Reuse caller-provided signals (architect Phase 7 path). Filled in Task 7."""
    return []
