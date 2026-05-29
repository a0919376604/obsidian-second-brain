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


def test_build_ai_memory_prompt_requires_11_block_keys():
    from scripts.architect.sections import build_ai_memory_prompt

    prompt = build_ai_memory_prompt(
        project="P",
        ai_memory_signals={
            "per_flow": {
                "engines": {
                    "has_memory": True,
                    "backends": ["redis"],
                    "checkpointer_classes": ["SimpleRedisSaver"],
                    "checkpointer_sources": ["backend/.../saver.py"],
                    "key_patterns": ["simple_ckpt_v2"],
                    "reducer_funcs": ["add_messages_limited"],
                    "reducer_caps": [{"name": "add_messages_limited", "limit": 100, "source": "..."}],
                    "compaction_funcs": ["session_summary"],
                    "compaction_sources": ["..."],
                }
            },
            "summary": {"memory_flows": 1, "stateless_flows": 0,
                        "primary_backend": "redis", "uniform_backend": True},
        },
        ai_flows_summary=[{"slug": "engines", "framework": "langgraph",
                           "root_path": "backend/engines/langgraph"}],
        output_lang="zh-TW",
    )
    for key in (
        "summary", "flow-memory-map", "backend-and-storage",
        "scope-and-lifecycle", "context-window-management",
        "compaction-strategy", "long-term-vs-short", "strengths",
        "weaknesses", "improvements", "dependencies",
    ):
        assert key in prompt, f"prompt must reference block key {key!r}"


def test_build_ai_memory_prompt_no_invention_rule():
    """When a signal field is empty/null, prompt must instruct LLM to acknowledge absence."""
    from scripts.architect.sections import build_ai_memory_prompt

    prompt = build_ai_memory_prompt(
        project="P",
        ai_memory_signals={"per_flow": {}, "summary": {"memory_flows": 0,
                                                         "stateless_flows": 1,
                                                         "primary_backend": "none",
                                                         "uniform_backend": True}},
        ai_flows_summary=[],
        output_lang="zh-TW",
    )
    assert "未偵測到" in prompt or "acknowledge absence" in prompt.lower() or "no invention" in prompt.lower()


def test_build_ai_memory_prompt_wikilink_out_directive():
    """Prompt MUST instruct LLM to wikilink-out per-flow state-schema rather than rewrite."""
    from scripts.architect.sections import build_ai_memory_prompt

    prompt = build_ai_memory_prompt(
        project="P",
        ai_memory_signals={"per_flow": {}, "summary": {"memory_flows": 0,
                                                         "stateless_flows": 0,
                                                         "primary_backend": "none",
                                                         "uniform_backend": True}},
        ai_flows_summary=[],
        output_lang="zh-TW",
    )
    assert "[[ai-flows/" in prompt
    assert "State schema" in prompt or "state-schema" in prompt
