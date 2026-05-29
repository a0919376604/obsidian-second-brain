"""Tests for scripts.architect.ai_rag_detect.detect_rag."""
from __future__ import annotations

from pathlib import Path

from scripts.architect.ai_rag_detect import detect_rag


def test_detects_weaviate_retrieve_role_read(tmp_path: Path):
    """Flow calling `.similarity_search` + `.hybrid` → role='read', vector_store=weaviate."""
    flow_root = tmp_path / "engines"
    flow_root.mkdir()
    (flow_root / "retrieve.py").write_text(
        "import weaviate\n"
        "from langchain_weaviate.vectorstores import WeaviateVectorStore\n"
        "vs = WeaviateVectorStore(client=weaviate.Client('http://x'))\n"
        "def retrieve(query):\n"
        "    return vs.similarity_search(query, k=12)\n",
        encoding="utf-8",
    )
    (flow_root / "embed.py").write_text(
        "from langchain_google_genai import GoogleGenerativeAIEmbeddings\n"
        "embedding = GoogleGenerativeAIEmbeddings(model='models/text-embedding-004')\n",
        encoding="utf-8",
    )

    class _Flow:
        slug = "engines"
        root_path = "engines"

    result = detect_rag(tmp_path, [_Flow()])
    fr = result["per_flow"]["engines"]
    assert fr["role"] == "read"
    assert "weaviate" in fr["vector_stores"]
    assert "google_generativeai" in fr["embedding_libs"]
    assert "models/text-embedding-004" in fr["embedding_models"]


def test_detects_top_k_and_alpha_params(tmp_path: Path):
    """Regex extracts top_k= and hybrid_alpha= from retrieve calls."""
    flow_root = tmp_path / "engines"
    flow_root.mkdir()
    (flow_root / "retrieve.py").write_text(
        "import weaviate\n"
        "def retrieve(query):\n"
        "    return search(query, top_k=12, hybrid_alpha=0.8, rerank_num=6)\n",
        encoding="utf-8",
    )

    class _Flow:
        slug = "engines"
        root_path = "engines"

    result = detect_rag(tmp_path, [_Flow()])
    params = result["per_flow"]["engines"]["retrieve_params"]
    assert params.get("top_k") == 12
    assert params.get("hybrid_alpha") == 0.8
    assert params.get("rerank_num") == 6
