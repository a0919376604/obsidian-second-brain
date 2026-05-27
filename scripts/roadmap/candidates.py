"""Phase 1 — gap candidate detection from Architecture/ files.

Reads future.md / decisions.md / roadmap.md, extracts bullets from known
sections, normalizes + deduplicates, returns ordered Candidate list.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Candidate:
    id: str
    title: str
    source_wikilink: str
    source_line: int
    kind: str
    raw_text: str
    # v3 additions (optional, populated when source is a structured Improvement).
    why: str | None = None
    evidence: list[str] = field(default_factory=list)
    effort: str | None = None
    risk_if_not_done: str | None = None
    confidence: str | None = None


# Section heading -> (kind, source-file)
_FUTURE_SECTIONS = {
    "## 已知限制": "limitation",
    "## Known limitations": "limitation",
    "## 落差分析": "gap",
    "## Gap analysis": "gap",
    "## 期望中的想法": "aspiration",
    "## Aspirational ideas": "aspiration",
}

_DECISIONS_SECTIONS = {
    "## 建議升級為 ADR": "promote-to-adr",
    "## Promote to ADR": "promote-to-adr",
}

_ROADMAP_SECTIONS = {
    "## TODO 群組": "todo-cluster",
    "## TODO clusters": "todo-cluster",
}

_BULLET_RE = re.compile(r"^[-*]\s+(.+)$", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)


def detect_candidates(project_root: Path) -> list[Candidate]:
    """Walk Architecture/ subfiles, extract candidates, dedup, return.

    v3: prefers `## 改進機會` / `## Improvement opportunities` blocks from any
    architect file (overview.md, features.md, modules/*.md, flows.md, jobs.md).
    Each Imp becomes a fully-structured Candidate. v2 sections (future.md
    落差分析 / 期望中的想法 / decisions.md Promote-to-ADR) are still consulted
    as supplementary signal.
    """
    arch = project_root / "Architecture"
    if not arch.is_dir():
        return []
    out: list[Candidate] = []
    # v3 improvements — walk every architect file.
    files = list(arch.glob("*.md")) + list((arch / "modules").glob("*.md"))
    for f in files:
        out.extend(_extract_improvements_from_file(f, arch))
    # v2 legacy signals.
    out.extend(_extract_from_file(arch / "future.md", _FUTURE_SECTIONS))
    out.extend(_extract_from_file(arch / "decisions.md", _DECISIONS_SECTIONS))
    out.extend(_extract_from_file(arch / "roadmap.md", _ROADMAP_SECTIONS, freq_dedup=True))
    return _dedup(out)


def _extract_improvements_from_file(path: Path, arch_root: Path) -> list[Candidate]:
    """Pull `## 改進機會` / `## Improvement opportunities` blocks via sections.parse_improvements_block."""
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    # Locate the H2 block body.
    pattern = re.compile(
        r"^##\s+(?:改進機會|Improvement opportunities)\s*$([\s\S]*?)(?=^##\s|\Z)",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return []
    body = m.group(1)
    rel_path = path.relative_to(arch_root.parent).as_posix()
    # Use the same parser sections.py exposes.
    from scripts.architect.sections import parse_improvements_block
    imps = parse_improvements_block(body)
    out: list[Candidate] = []
    arch_rel = rel_path.replace(".md", "")
    anchor = "改進機會" if "改進機會" in text else "Improvement opportunities"
    for imp in imps:
        cand_id = _make_id("imp", _normalize_title(imp.title))
        out.append(Candidate(
            id=cand_id,
            title=imp.title,
            source_wikilink=f"[[{arch_rel}#{anchor}]]",
            source_line=0,
            kind="improvement",
            raw_text=imp.why,
            why=imp.why,
            evidence=imp.evidence,
            effort=imp.effort,
            risk_if_not_done=imp.risk_if_not_done,
            confidence=imp.confidence,
        ))
    return out


def _extract_from_file(path: Path, section_to_kind: dict[str, str], freq_dedup: bool = False) -> list[Candidate]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    out: list[Candidate] = []
    file_stem = path.stem  # e.g. "future"
    arch_rel = f"Architecture/{file_stem}"
    for heading_str, kind in section_to_kind.items():
        body, body_start_line = _section_body(text, heading_str)
        if body is None:
            continue
        anchor = heading_str.lstrip("# ").strip()
        # For todo-cluster, count frequency by normalized TODO body.
        bullets = _BULLET_RE.findall(body) + _NUMBERED_RE.findall(body)
        freq: dict[str, int] = {}
        first_raw: dict[str, str] = {}
        for b in bullets:
            key = _todo_cluster_key(b) if freq_dedup else b
            freq[key] = freq.get(key, 0) + 1
            first_raw.setdefault(key, b)
        for key, count in freq.items():
            if freq_dedup and count < 2:
                continue
            raw = first_raw[key]
            title = _normalize_title(raw)
            cand_id = _make_id(kind, title)
            # Approximate source_line as body_start_line; precise per-bullet line tracking is overkill.
            out.append(Candidate(
                id=cand_id,
                title=title or raw,
                source_wikilink=f"[[{arch_rel}#{anchor}]]",
                source_line=body_start_line,
                kind=kind,
                raw_text=raw.strip(),
            ))
    return out


def _section_body(text: str, heading: str) -> tuple[str | None, int]:
    """Return (body, 1-indexed start line) for the section whose H2 matches `heading`."""
    pattern = re.compile(rf"^{re.escape(heading)}\s*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return None, 0
    start = m.end()
    start_line = text[: m.start()].count("\n") + 1
    # Body until next H2 or EOF.
    rest = text[start:]
    next_h2 = re.search(r"\n##\s+", rest)
    end = start + (next_h2.start() if next_h2 else len(rest))
    return text[start:end].strip(), start_line


_PUNCT_RE = re.compile(r"[「」、,。!?:;]+")
_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+")


def _normalize_title(raw: str) -> str:
    s = raw.strip()
    s = _EMOJI_RE.sub("", s)
    s = _PUNCT_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    # Strip leading inline-markdown like **bold** wrapper.
    s = re.sub(r"^\**\s*", "", s).rstrip("*").strip()
    # Cap length to keep IDs short.
    return s[:120]


_TODO_PREFIX_RE = re.compile(r"^`[^`]+`\s+\(TODO\)\s+", re.IGNORECASE)


def _todo_cluster_key(raw: str) -> str:
    return _normalize_title(_TODO_PREFIX_RE.sub("", raw))


def _make_id(kind: str, normalized_title: str) -> str:
    h = hashlib.sha1(f"{kind}::{normalized_title}".encode("utf-8")).hexdigest()[:10]
    return f"{kind[:3]}-{h}"


def _dedup(cands: list[Candidate]) -> list[Candidate]:
    """Drop later occurrences of candidates with the same normalized title."""
    seen: set[str] = set()
    out: list[Candidate] = []
    for c in cands:
        key = c.title.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out
