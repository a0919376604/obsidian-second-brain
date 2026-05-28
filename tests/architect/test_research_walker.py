"""Tests for scripts.architect.research_walker.collect_research_excerpts."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.architect.research_walker import collect_research_excerpts

FIXTURE = Path(__file__).parent / "fixtures" / "vault_with_research"


def test_walks_research_dir_recursively():
    """Both top-level and sub/ research notes are returned."""
    excerpts = collect_research_excerpts(FIXTURE)
    paths = [e["path"] for e in excerpts]
    assert any(p.endswith("A.md") for p in paths), f"missing A.md; got {paths}"
    assert any(p.endswith("B.md") for p in paths), f"missing B.md; got {paths}"


def test_excerpt_fields_populated_from_frontmatter():
    """Each excerpt has title, first_para, tags, date keys."""
    excerpts = collect_research_excerpts(FIXTURE)
    a = next(e for e in excerpts if e["path"].endswith("A.md"))
    assert a["title"] == "LINE bot 趨勢 2026"
    assert a["date"] == "2026-04-15"
    assert "competitor" in a["tags"]
    assert "LINE 官方 2026 Q1" in a["first_para"]
    assert len(a["first_para"]) <= 500


def test_ordered_by_date_desc():
    """Most recent date first."""
    excerpts = collect_research_excerpts(FIXTURE)
    assert excerpts[0]["date"] >= excerpts[-1]["date"]
    # A (2026-04) before B (2026-03)
    assert excerpts[0]["path"].endswith("A.md")
