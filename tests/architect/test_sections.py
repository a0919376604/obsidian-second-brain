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
