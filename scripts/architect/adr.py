"""Discover existing decision documents (ADRs, ARCHITECTURE.md, DESIGN.md).

Returns a list of DecisionDoc records describing each found file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ADR_DIRS = ("docs/adr", "docs/decisions", "architecture/decisions", "doc/adr")
_TOP_LEVEL_DOCS = (("ARCHITECTURE.md", "architecture-doc"), ("DESIGN.md", "design-doc"))


@dataclass
class DecisionDoc:
    path: str         # repo-relative posix path
    title: str        # first H1 or fallback to filename stem
    kind: str         # adr / architecture-doc / design-doc


def discover_decision_docs(repo_root: Path) -> list[DecisionDoc]:
    repo_root = repo_root.resolve()
    out: list[DecisionDoc] = []
    for d in _ADR_DIRS:
        adr_dir = repo_root / d
        if adr_dir.is_dir():
            for p in sorted(adr_dir.rglob("*.md")):
                out.append(DecisionDoc(
                    path=p.relative_to(repo_root).as_posix(),
                    title=_extract_title(p),
                    kind="adr",
                ))
    for filename, kind in _TOP_LEVEL_DOCS:
        p = repo_root / filename
        if p.is_file():
            out.append(DecisionDoc(
                path=p.relative_to(repo_root).as_posix(),
                title=_extract_title(p),
                kind=kind,
            ))
    return out


_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _extract_title(p: Path) -> str:
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.stem
    m = _H1_RE.search(text)
    return m.group(1).strip() if m else p.stem
