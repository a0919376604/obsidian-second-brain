"""v4.6 companion archetype section registration tests."""
from __future__ import annotations

from scripts.architect.sections import SECTION_TYPES, _BLOCK_NAMES, _BLOCK_HEADINGS


def test_character_card_section_type_present():
    assert SECTION_TYPES["character-card"] == "architecture-character-card"


def test_world_section_type_present():
    assert SECTION_TYPES["world"] == "architecture-world"


def test_storyline_section_type_present():
    assert SECTION_TYPES["storyline"] == "architecture-storyline"


def test_companion_overview_section_type_present():
    assert SECTION_TYPES["companion-overview"] == "architecture-companion-overview"


def test_character_card_block_names_v4_6():
    expected = (
        "summary", "card-schema", "definitions-inventory",
        "prompt-template-binding", "versioning-and-overrides",
        "strengths", "weaknesses", "improvements", "dependencies",
    )
    assert _BLOCK_NAMES["character-card"] == expected


def test_world_block_names_v4_6():
    expected = (
        "summary", "world-schema", "lore-inventory", "world-state",
        "loading-strategy", "mutation-rules",
        "strengths", "weaknesses", "improvements", "dependencies",
    )
    assert _BLOCK_NAMES["world"] == expected


def test_storyline_block_names_v4_6():
    expected = (
        "summary", "storyline-dsl", "state-machine", "progression-rules",
        "branching-logic", "persistence", "authoring-workflow",
        "strengths", "weaknesses", "improvements", "dependencies",
    )
    assert _BLOCK_NAMES["storyline"] == expected


def test_companion_overview_block_names_v4_6():
    expected = (
        "summary", "four-layer-diagram", "data-flow", "bind-points",
        "layer-maturity-table",
        "strengths", "weaknesses", "improvements", "dependencies",
    )
    assert _BLOCK_NAMES["companion-overview"] == expected


def test_v4_6_new_block_headings_registered():
    """All v4.6-specific block names must have entries in _BLOCK_HEADINGS."""
    new_blocks = [
        "card-schema", "definitions-inventory", "prompt-template-binding",
        "versioning-and-overrides",
        "world-schema", "lore-inventory", "world-state",
        "loading-strategy", "mutation-rules",
        "storyline-dsl", "state-machine", "progression-rules",
        "branching-logic", "persistence", "authoring-workflow",
        "four-layer-diagram", "data-flow", "bind-points",
        "layer-maturity-table",
    ]
    for block in new_blocks:
        assert block in _BLOCK_HEADINGS, f"missing heading for {block}"
