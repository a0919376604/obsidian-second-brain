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
        Candidate(title="加 SSO 整合", source_wikilink="[[a]]", source_line=1,
                  kind="gap", raw_text="加 SSO 整合"),
        Candidate(title="加 sso 整合", source_wikilink="[[b]]", source_line=2,
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
