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


def test_build_ai_rag_prompt_requires_11_block_keys():
    from scripts.architect.sections import build_ai_rag_prompt

    prompt = build_ai_rag_prompt(
        project="P",
        ai_rag_signals={
            "per_flow": {
                "writer": {"role": "write", "vector_stores": ["weaviate"],
                           "embedding_libs": ["openai"],
                           "embedding_models": ["text-embedding-3-small"],
                           "retrieve_params": {}, "rerank_libs": [], "chunking": None,
                           "vector_store_sources": [], "embedding_dims": None},
                "reader": {"role": "read", "vector_stores": ["weaviate"],
                           "embedding_libs": ["google_generativeai"],
                           "embedding_models": ["models/text-embedding-004"],
                           "retrieve_params": {"hybrid_alpha": 0.8, "top_k": 12},
                           "rerank_libs": [], "chunking": None,
                           "vector_store_sources": [], "embedding_dims": None},
            },
            "summary": {"read_flows": 1, "write_flows": 1,
                        "vector_stores": ["weaviate"], "primary_vector_store": "weaviate",
                        "embedding_aligned": False,
                        "alignment_mismatch": [{"write": {"flow": "writer",
                                                          "model": "text-embedding-3-small"},
                                                 "read": {"flow": "reader",
                                                          "model": "models/text-embedding-004"}}]},
        },
        ai_flows_summary=[
            {"slug": "writer", "framework": "custom-pipeline", "root_path": "modules/writer"},
            {"slug": "reader", "framework": "langgraph", "root_path": "backend/reader"},
        ],
        output_lang="zh-TW",
    )
    for key in (
        "summary", "rag-data-flow", "ingest-pipeline", "vector-store-config",
        "retrieve-strategy", "embedding-providers", "evaluation",
        "strengths", "weaknesses", "improvements", "dependencies",
    ):
        assert key in prompt, f"prompt must reference {key!r}"


def test_build_ai_rag_prompt_embedding_aligned_false_warning():
    """When embedding_aligned=false, prompt MUST instruct LLM to flag mismatch in
    weaknesses + improvements blocks."""
    from scripts.architect.sections import build_ai_rag_prompt

    prompt = build_ai_rag_prompt(
        project="P",
        ai_rag_signals={
            "per_flow": {},
            "summary": {"read_flows": 1, "write_flows": 1,
                        "vector_stores": ["weaviate"], "primary_vector_store": "weaviate",
                        "embedding_aligned": False, "alignment_mismatch": []},
        },
        ai_flows_summary=[],
        output_lang="zh-TW",
    )
    assert "embedding_aligned" in prompt or "embedding-aligned" in prompt
    assert "false" in prompt.lower()
    assert "weakness" in prompt.lower() or "缺點" in prompt
    assert "improvement" in prompt.lower() or "改進" in prompt


def test_build_ai_rag_prompt_aligned_true_no_warning():
    """When embedding_aligned=true, prompt should NOT push a misalignment warning."""
    from scripts.architect.sections import build_ai_rag_prompt

    prompt = build_ai_rag_prompt(
        project="P",
        ai_rag_signals={
            "per_flow": {},
            "summary": {"read_flows": 1, "write_flows": 1,
                        "vector_stores": ["weaviate"], "primary_vector_store": "weaviate",
                        "embedding_aligned": True, "alignment_mismatch": []},
        },
        ai_flows_summary=[],
        output_lang="zh-TW",
    )
    # The prompt MUST NOT insist on a misalignment Imp.
    assert "MUST flag the mismatch" not in prompt
