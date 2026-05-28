from pathlib import Path

from scripts.architect.ai_flow import AIFlow, detect_ai_flows

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_detects_langgraph_project():
    flows = detect_ai_flows(FIXTURE_DIR / "langgraph_proj")
    assert len(flows) == 1
    f = flows[0]
    assert f.framework == "langgraph"
    assert f.node_count >= 3
    assert "app" in f.root_path or "graph" in f.root_path
    assert any("prompts" in p for p in f.prompt_files)


def test_detects_custom_pipeline_project():
    flows = detect_ai_flows(FIXTURE_DIR / "custom_pipeline_proj")
    assert len(flows) == 1
    f = flows[0]
    assert f.framework == "custom-pipeline"
    assert "pipeline" in f.root_path
    assert any("prompts.toml" in p for p in f.prompt_files)


def test_detects_no_ai_in_flask_project():
    flows = detect_ai_flows(FIXTURE_DIR / "no_ai_proj")
    assert flows == []


def test_node_count_threshold_enforced(tmp_path: Path):
    """Project with langgraph dep but only 1 node should NOT count as AI flow."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "tiny"\ndependencies = ["langgraph"]\n'
    )
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "graph.py").write_text(
        'from langgraph.graph import StateGraph\n'
        'g = StateGraph(dict)\n'
        'g.add_node("only", lambda s: s)\n'  # ONLY 1 node
    )
    flows = detect_ai_flows(tmp_path)
    assert flows == []


def test_ai_flow_slug_is_filename_safe():
    """AIFlow.slug must be ascii lowercase hyphen — usable as filename."""
    import re
    flows = detect_ai_flows(FIXTURE_DIR / "langgraph_proj")
    for f in flows:
        assert re.match(r"^[a-z0-9-]+$", f.slug), f"bad slug: {f.slug!r}"
