from pathlib import Path

from scripts.roadmap.candidates import Candidate, detect_candidates

FIXTURE = Path(__file__).parent / "fixtures" / "project-a"


def test_detects_future_md_buckets():
    cands = detect_candidates(FIXTURE)
    kinds = {c.kind for c in cands}
    assert "limitation" in kinds
    assert "gap" in kinds
    assert "aspiration" in kinds


def test_detects_promote_to_adr():
    cands = detect_candidates(FIXTURE)
    promotes = [c for c in cands if c.kind == "promote-to-adr"]
    assert len(promotes) == 3
    assert any("Redis Cluster" in c.raw_text for c in promotes)


def test_detects_todo_clusters_only_when_frequency_ge_2():
    cands = detect_candidates(FIXTURE)
    clusters = [c for c in cands if c.kind == "todo-cluster"]
    # OAuth-flow TODOs appear 3 times in backend, 2 times in frontend -> 2 clusters
    assert len(clusters) >= 1
    assert any("OAuth" in c.raw_text for c in clusters)


def test_candidate_carries_source_wikilink():
    cands = detect_candidates(FIXTURE)
    for c in cands:
        if c.kind == "gap":
            assert c.source_wikilink.startswith("[[Architecture/future")
            return
    raise AssertionError("no gap candidate found")


def test_dedup_by_normalized_title():
    # Two candidates with same text after lowercasing + stripping punct should dedup
    from scripts.roadmap.candidates import Candidate, _dedup
    cands = [
        Candidate(id="gap-a", title="加 SSO 整合", source_wikilink="[[a]]", source_line=1,
                  kind="gap", raw_text="加 SSO 整合"),
        Candidate(id="asp-b", title="加 sso 整合", source_wikilink="[[b]]", source_line=2,
                  kind="aspiration", raw_text="加 sso 整合"),
    ]
    result = _dedup(cands)
    assert len(result) == 1


def test_missing_architecture_dir_returns_empty(tmp_path: Path):
    assert detect_candidates(tmp_path) == []


def test_candidate_has_stable_id():
    """Candidate id should be deterministic from kind + normalized title."""
    cands = detect_candidates(FIXTURE)
    ids = [c.id for c in cands]
    assert len(ids) == len(set(ids))  # all unique
    # Re-run yields same IDs
    cands2 = detect_candidates(FIXTURE)
    assert [c.id for c in cands2] == ids


def test_candidate_supports_v3_improvement_fields():
    from scripts.roadmap.candidates import Candidate
    c = Candidate(
        id="imp-x",
        title="Extract worker",
        source_wikilink="[[modules/backend#改進機會]]",
        source_line=0,
        kind="improvement",
        raw_text="full body",
        why="Because.",
        evidence=["[[a]]"],
        effort="M",
        risk_if_not_done="Bad.",
        confidence="medium",
    )
    assert c.why == "Because."
    assert c.effort == "M"
    assert c.confidence == "medium"


def test_candidate_v2_fields_still_work():
    """Existing v2 candidates without Imp metadata still construct fine."""
    from scripts.roadmap.candidates import Candidate
    c = Candidate(
        id="gap-x",
        title="A gap",
        source_wikilink="[[Architecture/future#落差分析]]",
        source_line=10,
        kind="gap",
        raw_text="...",
    )
    assert c.why is None
    assert c.effort is None


def test_detect_candidates_reads_improvement_blocks_from_modules(tmp_path):
    """v3 — `## 改進機會` / `## Improvement opportunities` blocks in modules/*.md become candidates."""
    from scripts.roadmap.candidates import detect_candidates
    arch = tmp_path / "Architecture"
    (arch / "modules").mkdir(parents=True)
    # A v3 module note with an improvement block.
    (arch / "modules" / "backend.md").write_text(
        "## 改進機會\n\n"
        "### Imp 1: 拆 EventConsumer 為獨立 worker\n"
        "- **為什麼:** API process 與 event loop 共用\n"
        "- **證據:** [[Architecture/decisions#Event routing principle]]\n"
        "- **Effort:** M\n"
        "- **未做的風險:** 流量峰值 API 延遲飆\n"
        "- **Confidence:** medium\n"
        "\n"
        "### Imp 2: 加 webhook signature verification\n"
        "- **為什麼:** 目前未驗證 LINE 來源\n"
        "- **證據:** `backend/main.py:80`\n"
        "- **Effort:** S\n"
        "- **未做的風險:** webhook 可被偽造\n"
        "- **Confidence:** stated\n"
    )
    # future.md still contributes via known-limitations (v3 keeps this section).
    (arch / "future.md").write_text(
        "## 已知限制\n"
        "- 沒有 SSO 整合 (stated)\n"
    )
    cands = detect_candidates(tmp_path)
    # 2 improvements from backend module + 1 limitation from future.md
    by_kind = {c.kind: [x for x in cands if x.kind == c.kind] for c in cands}
    imp_titles = [c.title for c in cands if c.kind == "improvement"]
    assert any("EventConsumer" in t for t in imp_titles)
    assert any("webhook signature" in t for t in imp_titles)
    # Improvement candidate carries Imp metadata.
    ec_cand = next(c for c in cands if c.kind == "improvement" and "EventConsumer" in c.title)
    assert ec_cand.effort == "M"
    assert ec_cand.confidence == "medium"
    assert any("Event routing" in e for e in ec_cand.evidence)
    # Limitation still picked up.
    assert any(c.kind == "limitation" for c in cands)


def test_detect_candidates_reads_improvements_from_overview(tmp_path):
    """Overview-level Imps also become candidates."""
    from scripts.roadmap.candidates import detect_candidates
    arch = tmp_path / "Architecture"
    arch.mkdir(parents=True)
    (arch / "overview.md").write_text(
        "## 改進機會\n\n"
        "### Imp 1: 升級 LangGraph 為 pluggable adapter\n"
        "- **為什麼:** 目前只能跑 LangGraph,鎖死供應商\n"
        "- **證據:** [[Architecture/decisions]]\n"
        "- **Effort:** L\n"
        "- **未做的風險:** 換模型成本高\n"
        "- **Confidence:** stated\n"
    )
    cands = detect_candidates(tmp_path)
    imp = [c for c in cands if c.kind == "improvement"]
    assert len(imp) == 1
    assert "LangGraph" in imp[0].title
    assert imp[0].effort == "L"


def test_detect_candidates_v2_fallback_when_no_improvement_blocks(tmp_path):
    """If no `## 改進機會` blocks exist (legacy v2 vault), fall back to v2 detection."""
    from scripts.roadmap.candidates import detect_candidates
    arch = tmp_path / "Architecture"
    arch.mkdir(parents=True)
    (arch / "future.md").write_text(
        "## 落差分析\n\n- README mentions streaming, not implemented\n"
        "## 期望中的想法\n\n- migrate to pluggable engines\n"
    )
    cands = detect_candidates(tmp_path)
    # Should still find these legacy candidates.
    kinds = {c.kind for c in cands}
    assert "gap" in kinds
    assert "aspiration" in kinds
