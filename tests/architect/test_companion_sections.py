"""v4.6 companion archetype section registration tests."""
from __future__ import annotations

from scripts.architect.sections import SECTION_TYPES, _BLOCK_NAMES, _BLOCK_HEADINGS


def test_character_card_section_type_present():
    assert SECTION_TYPES["character-card"] == "architecture-character-card"


def test_world_section_type_present():
    assert SECTION_TYPES["world"] == "architecture-world"


def test_storyline_section_type_present():
    assert SECTION_TYPES["storyline"] == "architecture-storyline"


def test_companion_overview_section_type_present():
    assert SECTION_TYPES["companion-overview"] == "architecture-companion-overview"


def test_character_card_block_names_v4_6():
    expected = (
        "summary", "card-schema", "definitions-inventory",
        "prompt-template-binding", "versioning-and-overrides",
        "strengths", "weaknesses", "improvements", "dependencies",
    )
    assert _BLOCK_NAMES["character-card"] == expected


def test_world_block_names_v4_6():
    expected = (
        "summary", "world-schema", "lore-inventory", "world-state",
        "loading-strategy", "mutation-rules",
        "strengths", "weaknesses", "improvements", "dependencies",
    )
    assert _BLOCK_NAMES["world"] == expected


def test_storyline_block_names_v4_6():
    expected = (
        "summary", "storyline-dsl", "state-machine", "progression-rules",
        "branching-logic", "persistence", "authoring-workflow",
        "strengths", "weaknesses", "improvements", "dependencies",
    )
    assert _BLOCK_NAMES["storyline"] == expected


def test_companion_overview_block_names_v4_6():
    expected = (
        "summary", "four-layer-diagram", "data-flow", "bind-points",
        "layer-maturity-table",
        "strengths", "weaknesses", "improvements", "dependencies",
    )
    assert _BLOCK_NAMES["companion-overview"] == expected


def test_v4_6_new_block_headings_registered():
    """All v4.6-specific block names must have entries in _BLOCK_HEADINGS."""
    new_blocks = [
        "card-schema", "definitions-inventory", "prompt-template-binding",
        "versioning-and-overrides",
        "world-schema", "lore-inventory", "world-state",
        "loading-strategy", "mutation-rules",
        "storyline-dsl", "state-machine", "progression-rules",
        "branching-logic", "persistence", "authoring-workflow",
        "four-layer-diagram", "data-flow", "bind-points",
        "layer-maturity-table",
    ]
    for block in new_blocks:
        assert block in _BLOCK_HEADINGS, f"missing heading for {block}"


def test_scan_report_includes_ai_companion_key(tmp_path):
    """build_scan_report exposes ai_companion key when archetype detected."""
    import subprocess
    import os
    from scripts.architect.scan import build_scan_report

    # Minimal git repo so scanner doesn't crash on git metadata.
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("r\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("a\n", encoding="utf-8")
    chars = tmp_path / "characters"
    chars.mkdir()
    (chars / "alice.json").write_text('{"name":"Alice"}', encoding="utf-8")
    (tmp_path / "storyline.py").write_text(
        "# storyline beat / progression\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True,
        env={**os.environ, "GIT_AUTHOR_DATE": "2026-05-29T00:00:00",
             "GIT_COMMITTER_DATE": "2026-05-29T00:00:00"},
    )

    report = build_scan_report(tmp_path, vault_project_dir=None)
    assert "ai_companion" in report
    assert report["ai_companion"]["archetype"] == "ai-companion"
    assert report["ai_companion"]["layers"]["character-card"]["present"] is True


def test_scan_report_ai_companion_none_when_no_signals(tmp_path):
    """No character/storyline → archetype=none, key still present."""
    import subprocess
    import os
    from scripts.architect.scan import build_scan_report

    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("r\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("a\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("def hello(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True,
        env={**os.environ, "GIT_AUTHOR_DATE": "2026-05-29T00:00:00",
             "GIT_COMMITTER_DATE": "2026-05-29T00:00:00"},
    )

    report = build_scan_report(tmp_path, vault_project_dir=None)
    assert "ai_companion" in report
    assert report["ai_companion"]["archetype"] == "none"


def test_build_character_card_prompt_requires_9_block_keys():
    from scripts.architect.sections import build_character_card_prompt
    prompt = build_character_card_prompt(
        project="ai-eden",
        layer_evidence={"present": True, "root_paths": ["app/characters/"],
                         "artifact_files": ["app/characters/schema.py"],
                         "confidence": "high"},
        repomix_packed="<files>...</files>",
        output_lang="zh-TW",
    )
    for key in ("summary", "card-schema", "definitions-inventory",
                "prompt-template-binding", "versioning-and-overrides",
                "strengths", "weaknesses", "improvements", "dependencies"):
        assert key in prompt


def test_compose_character_card_note_emits_extra_frontmatter():
    from scripts.architect.sections import compose_character_card_note
    blocks = {n: f"body for {n}" for n in (
        "summary", "card-schema", "definitions-inventory",
        "prompt-template-binding", "versioning-and-overrides",
        "strengths", "weaknesses", "improvements", "dependencies",
    )}
    note = compose_character_card_note(
        project="P", repo_label="local: /tmp/p", commit="abc",
        signal_sources=["scan: ai_companion"], confidence="high",
        output_lang="zh-TW", generated_blocks=blocks,
        card_count=6, schema_version="v1",
    )
    assert "card-count: 6" in note
    assert "schema-version: v1" in note
    assert "layer: character-card" in note
