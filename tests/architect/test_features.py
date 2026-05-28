"""v4.2 features.md tests."""
from __future__ import annotations

from scripts.architect.sections import (
    DEPRECATED_SECTIONS,
    SECTION_TYPES,
    _BLOCK_HEADINGS,
    _BLOCK_NAMES,
)


def test_features_section_not_deprecated_in_v4_2():
    """v4.2 un-deprecates features. compose_note(section='features') should NOT
    log a deprecation warning."""
    assert "features" not in DEPRECATED_SECTIONS, (
        "features must be removed from DEPRECATED_SECTIONS in v4.2"
    )


def test_features_section_type_present():
    assert SECTION_TYPES["features"] == "architecture-features"


def test_features_v4_2_block_names():
    """v4.2 features has 10 @generated blocks in a specific order."""
    expected = (
        "summary",
        "capability-inventory",
        "product-coverage",
        "limitations",
        "strengths",
        "weaknesses",
        "missing-features",
        "improvements",
        "doc-sync-actions",
        "dependencies",
    )
    assert _BLOCK_NAMES["features"] == expected


def test_features_v4_2_block_headings_present():
    """Every block name in features has a heading in _BLOCK_HEADINGS."""
    for block_name in _BLOCK_NAMES["features"]:
        assert block_name in _BLOCK_HEADINGS, f"missing heading for {block_name}"


def test_features_new_block_headings_text():
    """v4.2 introduces 4 new block headings not used elsewhere."""
    assert _BLOCK_HEADINGS["capability-inventory"] == "## Capability inventory"
    assert _BLOCK_HEADINGS["product-coverage"] == "## Product coverage"
    assert _BLOCK_HEADINGS["limitations"] == "## Limitations"
    assert _BLOCK_HEADINGS["missing-features"] == "## Missing features"
    assert _BLOCK_HEADINGS["doc-sync-actions"] == "## Doc sync actions"
