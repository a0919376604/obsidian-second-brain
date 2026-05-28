from pathlib import Path

from scripts.architect.sections import (
    SECTION_NAMES,
    build_prompt,
    collect_signals,
    compose_note,
    signal_hash,
)


def test_signal_hash_is_deterministic():
    sig = {"foo": "bar", "list": [1, 2, 3]}
    assert signal_hash(sig) == signal_hash(sig)


def test_signal_hash_changes_on_value_change():
    a = signal_hash({"k": "v1"})
    b = signal_hash({"k": "v2"})
    assert a != b


def test_signal_hash_independent_of_dict_order():
    a = signal_hash({"a": 1, "b": 2})
    b = signal_hash({"b": 2, "a": 1})
    assert a == b


def test_section_names_constant():
    assert SECTION_NAMES == ("api-surface", "features", "decisions", "roadmap", "future")


def test_collect_signals_features():
    scan_report = {
        "readme_sections": {"Features": "- alpha\n- beta"},
        "api_surface": {"cli_commands": [{"name": "foo", "description": "do foo", "source": "src/cli.py:1"}],
                        "http_routes": [], "exports": [], "env_vars": [], "detection_status": "complete"},
        "decision_docs": [],
        "changelog": {"unreleased": None, "recent_versions": []},
        "todos": {},
        "stack": {},
    }
    manifest_modules = [{"slug": "cli", "description": "CLI front-end", "paths": ["src/cli.py"]}]
    sig = collect_signals("features", scan_report, manifest_modules)
    assert sig["readme_features"] == "- alpha\n- beta"
    assert sig["cli_commands"][0]["name"] == "foo"
    assert sig["modules"][0]["slug"] == "cli"


def test_collect_signals_roadmap_pulls_changelog_and_todos():
    scan_report = {
        "readme_sections": {"Roadmap": "- streaming"},
        "changelog": {"unreleased": "- soon", "recent_versions": [{"version": "0.1.0", "date": "2026-01-01", "body": "init"}]},
        "todos": {"cli": [{"path": "src/cli.py", "line": 1, "kind": "TODO", "label": "roadmap", "text": "rate-limit"}]},
    }
    sig = collect_signals("roadmap", scan_report, manifest_modules=[])
    assert sig["readme_roadmap"] == "- streaming"
    assert sig["changelog_unreleased"] == "- soon"
    assert sig["roadmap_todos"][0]["text"] == "rate-limit"


def test_build_prompt_en_lists_section_and_signals():
    prompt = build_prompt(
        section="features",
        signal={"readme_features": "- alpha", "cli_commands": [], "http_routes": [], "modules": []},
        output_lang="en",
        project="myproj",
    )
    assert "features" in prompt
    assert "English" in prompt or "en" in prompt
    assert "readme_features" in prompt


def test_build_prompt_zh_tw_demands_chinese_body_and_lists_dont_translate_rules():
    prompt = build_prompt(
        section="roadmap",
        signal={"readme_roadmap": "- streaming"},
        output_lang="zh-TW",
        project="myproj",
    )
    assert "繁體中文" in prompt or "zh-TW" in prompt
    # Spec §16.5 — must mention not-translating code identifiers.
    assert "code identifier" in prompt.lower() or "識別" in prompt or "檔名" in prompt


def test_compose_note_wraps_sentinels(tmp_path: Path):
    note = compose_note(
        section="features",
        project="myproj",
        repo_label="github.com/x/y",
        commit="abc1234",
        signal_sources=["README.md", "src/cli.py"],
        confidence="high",
        output_lang="en",
        generated_blocks={"summary": "We do X.", "capability-scope": "- alpha\n- beta"},
    )
    assert note.startswith("---\n")
    assert "type: architecture-features" in note
    assert "lang: en" in note
    assert "## For future Claude" in note
    assert "<!-- @generated:start summary -->" in note
    assert "We do X." in note
    assert "<!-- @generated:end summary -->" in note
    assert "<!-- @generated:start capability-scope -->" in note


def test_compose_note_zh_tw_uses_translated_headings():
    note = compose_note(
        section="features",
        project="myproj",
        repo_label="github.com/x/y",
        commit="abc1234",
        signal_sources=["README.md"],
        confidence="high",
        output_lang="zh-TW",
        generated_blocks={"summary": "做 X"},
    )
    assert "## 給未來 Claude" in note
    assert "## For future Claude" not in note
    assert "lang: zh-TW" in note


def test_compose_note_emits_h2_heading_before_each_block_en():
    """Each @generated block must be preceded by its canonical H2 heading,
    so Obsidian's outline + wikilink anchors work and the body is human-readable."""
    note = compose_note(
        section="api-surface",
        project="x",
        repo_label="github.com/x/y",
        commit="a",
        signal_sources=["a"],
        confidence="high",
        output_lang="en",
        generated_blocks={
            "summary": "API surface for x.",
            "interface-overview": "5 routes grouped by prefix.",
            "env-overview": "3 env vars grouped by prefix.",
        },
    )
    # H2 heading appears before each sentinel start.
    for h2, block in [
        ("## Summary", "summary"),
        ("## Interface overview", "interface-overview"),
        ("## Environment variables overview", "env-overview"),
    ]:
        assert h2 in note, f"missing H2 heading {h2!r}"
        # Heading must come before the sentinel start, not after.
        h2_idx = note.index(h2)
        sentinel_idx = note.index(f"<!-- @generated:start {block} -->")
        assert h2_idx < sentinel_idx, f"{h2!r} appears after its sentinel"


def test_compose_note_h2_headings_translate_to_zh_tw():
    note = compose_note(
        section="api-surface",
        project="x",
        repo_label="github.com/x/y",
        commit="a",
        signal_sources=["a"],
        confidence="high",
        output_lang="zh-TW",
        generated_blocks={
            "summary": "x 的介面",
            "interface-overview": "依前綴分組",
            "env-overview": "依前綴分組",
        },
    )
    # zh-TW headings appear; English originals must NOT appear in body.
    assert "## 摘要" in note
    assert "## 介面類型概觀" in note
    assert "## 環境變數概觀" in note
    assert "## Interface overview" not in note
    assert "## Environment variables overview" not in note


def test_compose_note_skips_h2_when_block_body_is_empty():
    """If a block has no body, neither the H2 nor the sentinels should appear."""
    note = compose_note(
        section="features",
        project="x",
        repo_label="github.com/x/y",
        commit="a",
        signal_sources=["a"],
        confidence="high",
        output_lang="en",
        generated_blocks={"summary": "Yes."},  # capability-map + notable-details intentionally omitted
    )
    assert "## Summary" in note
    assert "## Capability map" not in note
    assert "## Notable details" not in note
    assert "<!-- @generated:start capability-map -->" not in note


def test_repo_label_local_prefix_yields_local_path_field():
    from scripts.architect.sections import _repo_yaml_lines
    lines = _repo_yaml_lines("local: /Users/leric/Desktop/code/x")
    assert lines == ['local-path: "/Users/leric/Desktop/code/x"']


def test_repo_label_bare_abs_path_yields_local_path_field():
    from scripts.architect.sections import _repo_yaml_lines
    lines = _repo_yaml_lines("/abs/path/to/repo")
    assert lines == ['local-path: "/abs/path/to/repo"']


def test_repo_label_url_yields_quoted_repo_field():
    from scripts.architect.sections import _repo_yaml_lines
    lines = _repo_yaml_lines("github.com/x/y")
    assert lines == ['repo: "github.com/x/y"']


def test_compose_note_emits_no_double_colon_in_frontmatter():
    """The "repo: local: /path" YAML bug must not regress."""
    note = compose_note(
        section="module",
        project="x",
        repo_label="local: /tmp/foo",
        commit="a",
        signal_sources=["a"],
        confidence="medium",
        output_lang="zh-TW",
        generated_blocks={"scope": "test"},
    )
    # Extract frontmatter block.
    fm = note.split("---", 2)[1]
    # No line should have the pattern "key: word: " (double-colon-with-bare-value).
    for line in fm.splitlines():
        # Allow values that are quoted (real YAML strings).
        if ":" in line and line.count(":") > 1:
            # Must be quoted past the first colon.
            value = line.split(":", 1)[1].strip()
            assert value.startswith('"') and value.endswith('"'), \
                f"unquoted multi-colon in YAML: {line!r}"


def test_compose_note_insufficient_signal_status():
    note = compose_note(
        section="future",
        project="myproj",
        repo_label="github.com/x/y",
        commit="abc1234",
        signal_sources=[],
        confidence="low",
        output_lang="en",
        generated_blocks={},
        status="insufficient-signal",
    )
    assert "status: insufficient-signal" in note


def test_module_for_path_returns_slug():
    from scripts.architect.sections import module_for_path
    manifest = [
        {"slug": "auth", "paths": ["src/auth"]},
        {"slug": "api", "paths": ["src/api/routes.py"]},
    ]
    assert module_for_path("src/auth/login.py", manifest) == "auth"
    assert module_for_path("src/api/routes.py", manifest) == "api"
    assert module_for_path("random/orphan.py", manifest) is None


def test_render_signals_reviewed_en():
    from scripts.architect.sections import render_signals_reviewed
    out = render_signals_reviewed(
        sources=["CHANGELOG.md", "README.md#Roadmap"],
        todo_counts={"cli": 3, "api": 1},
        lang="en",
    )
    assert "CHANGELOG.md" in out
    assert "README.md#Roadmap" in out
    assert "cli: 3 TODOs" in out


def test_render_signals_reviewed_zh():
    from scripts.architect.sections import render_signals_reviewed
    out = render_signals_reviewed(sources=["CHANGELOG.md"], todo_counts={"cli": 2}, lang="zh-TW")
    assert "cli:" in out
    assert "2" in out


def test_gap_analysis_lists_mentioned_but_not_detected():
    from scripts.architect.sections import gap_analysis
    readme_features = "- Streaming HTTP\n- Plugin system\n- gRPC adapter\n"
    api = {
        "cli_commands": [],
        "http_routes": [{"method": "GET", "path": "/items"}],
        "exports": [{"symbol": "plugin_register", "kind": "named", "source": ""}],
        "env_vars": [],
    }
    gaps = gap_analysis(readme_features=readme_features, api_surface=api)
    # plugin_register suggests plugin system is implemented; streaming and gRPC are not.
    text = "\n".join(gaps)
    assert "Streaming" in text or "streaming" in text
    assert "gRPC" in text


def test_gap_analysis_empty_when_no_readme_features():
    from scripts.architect.sections import gap_analysis
    assert gap_analysis(readme_features="", api_surface={}) == []


def test_compose_function_note_en():
    from scripts.architect.sections import compose_function_note
    note = compose_function_note(
        project="myproj",
        repo_label="github.com/x/y",
        module_slug="cli",
        name="run",
        signature="def run(args: list[str]) -> int",
        source_file="src/cli.py",
        line_range="42-58",
        commit="abc1234",
        output_lang="en",
        generated_blocks={"what-it-does": "Entry point for CLI."},
    )
    assert "type: architecture-function" in note
    assert "module-slug: cli" in note
    assert "## Signature" in note
    assert "def run(args: list[str]) -> int" in note
    assert "Entry point for CLI." in note


def test_compose_function_note_zh_tw_translates_headings():
    from scripts.architect.sections import compose_function_note
    note = compose_function_note(
        project="myproj",
        repo_label="github.com/x/y",
        module_slug="cli",
        name="run",
        signature="def run() -> int",
        source_file="src/cli.py",
        line_range="42-58",
        commit="abc1234",
        output_lang="zh-TW",
        generated_blocks={"what-it-does": "CLI 入口點。"},
    )
    assert "## 函式簽章" in note
    assert "## 功能說明" in note


def test_compose_overview_en_emits_moc():
    from scripts.architect.sections import compose_overview
    note = compose_overview(
        project="myproj",
        repo_label="github.com/x/y",
        commit="abc1234",
        stack={"primary-language": "Python", "frameworks": ["FastAPI"]},
        output_lang="en",
        modules=[{"slug": "cli", "display_name": "CLI"}, {"slug": "api", "display_name": "API"}],
        entry_points=[{"path": "src/cli.py", "label": "pyproject.scripts.run", "kind": "pyproject"}],
        generated_blocks={
            "purpose": "We do things.",
            "layer-map": "```mermaid\ngraph TD\n  A --> B\n```",
            "external-deps": "- FastAPI 0.110",
            "key-abstractions": "- Module",
        },
    )
    assert "type: architecture-overview" in note
    assert "moc-style: true" in note
    assert "primary-language: Python" in note
    assert "## Capability MOC" in note
    assert "[[Architecture/features]]" in note
    assert "[[Architecture/api-surface]]" in note
    assert "[[modules/cli]]" in note
    assert "graph TD" in note


def test_compose_overview_zh_tw_translates_and_omits_empty_stack():
    from scripts.architect.sections import compose_overview
    note = compose_overview(
        project="myproj",
        repo_label="github.com/x/y",
        commit="abc1234",
        stack={},  # empty -> no stack block in frontmatter
        output_lang="zh-TW",
        modules=[],
        entry_points=[],
        generated_blocks={},
    )
    assert "## 給未來 Claude" in note
    assert "## 能力地圖 MOC" in note
    assert "stack:" not in note  # empty stack omitted per spec §5.7


def test_module_v3_block_names_are_judgment_focused():
    """v3 drops what-it-does/how-it-works/key-files; adds scope/strengths/weaknesses/improvements."""
    from scripts.architect.sections import _BLOCK_NAMES
    assert "module" in _BLOCK_NAMES
    names = set(_BLOCK_NAMES["module"])
    assert {"scope", "strengths", "weaknesses", "improvements", "dependencies"} <= names
    assert "key-files" not in names
    assert "what-it-does" not in names


def test_module_block_headings_translate():
    """Each v3 module block must have a heading entry."""
    from scripts.architect.sections import _BLOCK_HEADINGS
    from scripts.architect.lang import heading
    for block in ("scope", "strengths", "weaknesses", "improvements", "dependencies"):
        h_en = _BLOCK_HEADINGS[block]
        assert heading(h_en, "zh-TW") != h_en, f"{block} heading {h_en!r} has no zh-TW mapping"


def test_module_prompt_demands_judgment_not_description():
    """v3 module prompt must NOT ask for file lists; MUST ask for strengths/weaknesses/improvements."""
    from scripts.architect.sections import build_module_prompt
    prompt = build_module_prompt(
        module_slug="backend",
        repomix_packed="(packed code goes here)",
        agents_md_excerpt="(AGENTS.md excerpt)",
        output_lang="zh-TW",
    )
    # Must not ask for file listings
    assert "key files" not in prompt.lower()
    assert "list of files" not in prompt.lower()
    # Must ask for judgment blocks
    assert "strengths" in prompt
    assert "weaknesses" in prompt
    assert "improvement" in prompt.lower()
    # Each Imp must demand Evidence
    assert "evidence" in prompt.lower() or "Evidence" in prompt
    # zh-TW directive
    assert "繁體中文" in prompt or "zh-TW" in prompt


def test_module_prompt_en_no_chinese_directive():
    from scripts.architect.sections import build_module_prompt
    prompt = build_module_prompt(
        module_slug="backend",
        repomix_packed="",
        agents_md_excerpt="",
        output_lang="en",
    )
    assert "繁體中文" not in prompt
    assert "Evidence" in prompt or "evidence" in prompt


def test_module_prompt_demands_evidence_required_for_each_improvement():
    from scripts.architect.sections import build_module_prompt
    prompt = build_module_prompt(
        module_slug="backend", repomix_packed="", agents_md_excerpt="", output_lang="en",
    )
    # Prompt must say: if you can't cite evidence, don't include that improvement.
    assert "do not" in prompt.lower() or "skip" in prompt.lower() or "drop" in prompt.lower()
    # And mention the required Imp fields explicitly.
    for field in ("Why", "Evidence", "Effort", "Risk", "Confidence"):
        assert field in prompt, f"missing required Imp field {field!r}"


def test_render_improvement_block_uses_strict_h3_format():
    from scripts.architect.sections import render_improvements_block, ImprovementItem
    items = [
        ImprovementItem(
            title="Extract EventConsumer to separate worker container",
            why="API process shares CPU with event loop; peak traffic blocks request handling.",
            evidence=["[[Architecture/decisions#Event routing principle]]",
                      "`backend/main.py:120`"],
            effort="M",
            risk_if_not_done="During campaigns LINE webhook backlog grows; admin UI lags.",
            confidence="medium",
        ),
    ]
    rendered = render_improvements_block(items, lang="en")
    assert "### Imp 1: Extract EventConsumer to separate worker container" in rendered
    assert "- **Why:** API process shares CPU" in rendered
    assert "- **Evidence:**" in rendered
    assert "[[Architecture/decisions#Event routing principle]]" in rendered
    assert "`backend/main.py:120`" in rendered
    assert "- **Effort:** M" in rendered
    assert "- **Risk if not done:**" in rendered
    assert "- **Confidence:** medium" in rendered


def test_render_improvement_block_zh_tw():
    from scripts.architect.sections import render_improvements_block, ImprovementItem
    items = [
        ImprovementItem(
            title="拆 EventConsumer 為獨立 worker",
            why="API 跟 EventConsumer 共用 process",
            evidence=["[[Architecture/decisions]]"],
            effort="M",
            risk_if_not_done="流量峰值 API 飆延遲",
            confidence="medium",
        ),
    ]
    rendered = render_improvements_block(items, lang="zh-TW")
    assert "### Imp 1: 拆 EventConsumer 為獨立 worker" in rendered
    assert "**為什麼:**" in rendered
    assert "**證據:**" in rendered
    assert "**Effort:** M" in rendered
    assert "**未做的風險:**" in rendered
    assert "**Confidence:** medium" in rendered


def test_parse_improvements_block_round_trips_render():
    from scripts.architect.sections import (
        render_improvements_block, parse_improvements_block, ImprovementItem,
    )
    items = [
        ImprovementItem(
            title="A",
            why="Because.",
            evidence=["[[X]]", "`y.py:1`"],
            effort="S",
            risk_if_not_done="Bad.",
            confidence="high",
        ),
        ImprovementItem(
            title="B",
            why="Why B.",
            evidence=["[[Z]]"],
            effort="L",
            risk_if_not_done="Worse.",
            confidence="speculation",
        ),
    ]
    rendered = render_improvements_block(items, lang="en")
    parsed = parse_improvements_block(rendered)
    assert len(parsed) == 2
    assert parsed[0].title == "A"
    assert parsed[0].effort == "S"
    assert parsed[0].evidence == ["[[X]]", "`y.py:1`"]
    assert parsed[1].title == "B"
    assert parsed[1].confidence == "speculation"


def test_parse_improvements_block_zh_tw_labels():
    from scripts.architect.sections import parse_improvements_block
    text = (
        "### Imp 1: 拆 EventConsumer 為獨立 worker\n"
        "- **為什麼:** API 跟 EventConsumer 共用 process\n"
        "- **證據:** [[Architecture/decisions]]\n"
        "- **Effort:** M\n"
        "- **未做的風險:** 流量峰值 API 飆延遲\n"
        "- **Confidence:** medium\n"
    )
    items = parse_improvements_block(text)
    assert len(items) == 1
    assert items[0].title == "拆 EventConsumer 為獨立 worker"
    assert items[0].effort == "M"
    assert items[0].confidence == "medium"


def test_parse_improvements_block_skips_malformed():
    """An Imp with fewer than 5 required fields is dropped, not partially parsed."""
    from scripts.architect.sections import parse_improvements_block
    text = (
        "### Imp 1: Good one\n"
        "- **Why:** w\n"
        "- **Evidence:** [[E]]\n"
        "- **Effort:** S\n"
        "- **Risk if not done:** r\n"
        "- **Confidence:** high\n"
        "\n"
        "### Imp 2: Missing fields\n"
        "- **Why:** only this\n"
    )
    items = parse_improvements_block(text)
    assert len(items) == 1
    assert items[0].title == "Good one"


def test_enforce_improvements_cap_drops_extras():
    """When LLM returns 6 Imps but cap is 4, keep highest-confidence + first ones."""
    from scripts.architect.sections import ImprovementItem, enforce_improvements_cap
    items = [
        ImprovementItem(title=f"Imp {i}", why="w", evidence=["[[e]]"],
                        effort="M", risk_if_not_done="r",
                        confidence="medium" if i % 2 else "stated")
        for i in range(6)
    ]
    capped = enforce_improvements_cap(items, max_n=4)
    assert len(capped) == 4
    # Higher-confidence items should win over lower if cap forces choice.
    titles = [c.title for c in capped]
    # At least one `stated` confidence Imp survives.
    assert any(c.confidence == "stated" for c in capped)


def test_enforce_evidence_required_drops_imps_without_evidence():
    from scripts.architect.sections import ImprovementItem, enforce_evidence_required
    items = [
        ImprovementItem(title="A", why="w", evidence=["[[x]]"], effort="S",
                        risk_if_not_done="r", confidence="stated"),
        ImprovementItem(title="B", why="w", evidence=[], effort="S",
                        risk_if_not_done="r", confidence="stated"),
    ]
    filtered = enforce_evidence_required(items, require=True)
    assert len(filtered) == 1
    assert filtered[0].title == "A"
    # With require=False, both survive (debug mode).
    assert len(enforce_evidence_required(items, require=False)) == 2


def test_overview_v4_block_names_are_top_down_report():
    """v4 overview has 8 body sections matching the top-down report structure."""
    from scripts.architect.sections import _BLOCK_NAMES
    assert "overview" in _BLOCK_NAMES
    expected = (
        "purpose",
        "system-diagram",
        "stack-summary",
        "capabilities",
        "flows",
        "module-map",
        "cross-cutting-improvements",
        "drill-down",
    )
    assert _BLOCK_NAMES["overview"] == expected, \
        f"v4 overview should have these 8 blocks in order, got: {_BLOCK_NAMES['overview']}"


def test_deprecated_section_types_marked():
    """v4 marks 6 deprecated SECTION_TYPES entries (still callable for backward compat)."""
    from scripts.architect.sections import SECTION_TYPES, DEPRECATED_SECTIONS
    for s in ("api-surface", "features", "roadmap", "future", "jobs", "flows"):
        assert s in SECTION_TYPES, f"{s} still in SECTION_TYPES (kept for backward compat)"
        assert s in DEPRECATED_SECTIONS, f"{s} should be in DEPRECATED_SECTIONS"
