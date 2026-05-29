"""v4.3 AI memory + RAG cross-flow tests."""
from __future__ import annotations

from scripts.architect.sections import SECTION_TYPES, _BLOCK_NAMES, _BLOCK_HEADINGS


def test_ai_memory_section_type_present():
    assert SECTION_TYPES["ai-memory"] == "architecture-ai-memory"


def test_ai_rag_section_type_present():
    assert SECTION_TYPES["ai-rag"] == "architecture-ai-rag"


def test_ai_memory_block_names_v4_3():
    expected = (
        "summary",
        "flow-memory-map",
        "backend-and-storage",
        "scope-and-lifecycle",
        "context-window-management",
        "compaction-strategy",
        "long-term-vs-short",
        "strengths",
        "weaknesses",
        "improvements",
        "dependencies",
    )
    assert _BLOCK_NAMES["ai-memory"] == expected


def test_ai_rag_block_names_v4_3():
    expected = (
        "summary",
        "rag-data-flow",
        "ingest-pipeline",
        "vector-store-config",
        "retrieve-strategy",
        "embedding-providers",
        "evaluation",
        "strengths",
        "weaknesses",
        "improvements",
        "dependencies",
    )
    assert _BLOCK_NAMES["ai-rag"] == expected


def test_v4_3_new_block_headings_registered():
    """All v4.3-specific block names must have entries in _BLOCK_HEADINGS."""
    new_blocks = [
        "flow-memory-map", "backend-and-storage", "scope-and-lifecycle",
        "context-window-management", "compaction-strategy", "long-term-vs-short",
        "rag-data-flow", "ingest-pipeline", "vector-store-config",
        "retrieve-strategy", "embedding-providers",
    ]
    for block in new_blocks:
        assert block in _BLOCK_HEADINGS, f"missing heading for {block}"
