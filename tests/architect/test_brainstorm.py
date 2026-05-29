"""Tests for /obsidian-brainstorm section registration + helpers."""
from __future__ import annotations

from scripts.architect.sections import SECTION_TYPES, _BLOCK_NAMES, _BLOCK_HEADINGS


def test_brainstorm_section_type_present():
    assert SECTION_TYPES["brainstorm"] == "project-brainstorm"


def test_brainstorm_block_names_v1():
    expected = (
        "context",
        "opening-provocations",
        "drilled-explorations",
        "distilled-imps",
        "hypotheses",
        "parked",
        "open-questions",
        "meta-reflection",
        "dependencies",
    )
    assert _BLOCK_NAMES["brainstorm"] == expected


def test_brainstorm_block_headings_registered():
    """All v1 brainstorm block names must have entries in _BLOCK_HEADINGS."""
    new_blocks = [
        "context",
        "opening-provocations",
        "drilled-explorations",
        "distilled-imps",
        "hypotheses",
        "parked",
        "open-questions",
        "meta-reflection",
    ]
    for block in new_blocks:
        assert block in _BLOCK_HEADINGS, f"missing heading for {block}"
    # `dependencies` block reuses existing v3 mapping ("## Dependencies and consumers").
    assert "dependencies" in _BLOCK_HEADINGS
