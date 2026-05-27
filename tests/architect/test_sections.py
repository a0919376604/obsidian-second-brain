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
        generated_blocks={"summary": "We do X.", "capability-map": "- alpha\n- beta"},
    )
    assert note.startswith("---\n")
    assert "type: architecture-features" in note
    assert "lang: en" in note
    assert "## For future Claude" in note
    assert "<!-- @generated:start summary -->" in note
    assert "We do X." in note
    assert "<!-- @generated:end summary -->" in note
    assert "<!-- @generated:start capability-map -->" in note


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
            "cli-commands": "| Command | ... |",
            "http-routes": "| Method | ... |",
            "exports": "| Symbol | ... |",
            "env-vars": "| Var | ... |",
        },
    )
    # H2 heading appears before each sentinel start.
    for h2, block in [
        ("## Summary", "summary"),
        ("## CLI commands", "cli-commands"),
        ("## HTTP routes", "http-routes"),
        ("## Public exports", "exports"),
        ("## Environment variables", "env-vars"),
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
            "http-routes": "| 方法 | ... |",
            "env-vars": "| 變數 | ... |",
        },
    )
    # zh-TW headings appear; English originals must NOT appear in body.
    assert "## 摘要" in note
    assert "## HTTP 路由" in note
    assert "## 環境變數" in note
    assert "## HTTP routes" not in note
    assert "## Environment variables" not in note


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
