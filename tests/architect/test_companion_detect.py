"""Tests for scripts.architect.companion_detect.detect_companion_archetype."""
from __future__ import annotations

from pathlib import Path

from scripts.architect.companion_detect import (
    detect_companion_archetype,
    CompanionDetection,
    LayerEvidence,
)


def test_detect_companion_when_character_and_storyline_present(tmp_path: Path):
    """Both layers' signals → archetype=ai-companion, confidence=high."""
    chars = tmp_path / "app" / "characters"
    chars.mkdir(parents=True)
    (chars / "definitions").mkdir()
    (chars / "definitions" / "alice.json").write_text('{"name":"Alice"}', encoding="utf-8")
    (chars / "storyline.py").write_text(
        "# Storyline DSL\ndef beat(name): pass\n", encoding="utf-8"
    )

    result = detect_companion_archetype(repo_root=tmp_path, hub_frontmatter=None)
    assert isinstance(result, CompanionDetection)
    assert result.archetype == "ai-companion"
    assert result.confidence == "high"
    assert result.layers["character-card"].present is True
    assert result.layers["storyline"].present is True


def test_detect_no_companion_when_only_character(tmp_path: Path):
    """Character but NO storyline → archetype=none (generic LLM wrapper)."""
    chars = tmp_path / "app" / "characters"
    chars.mkdir(parents=True)
    (chars / "definitions").mkdir()
    (chars / "definitions" / "alice.json").write_text('{}', encoding="utf-8")
    # No storyline file.

    result = detect_companion_archetype(repo_root=tmp_path, hub_frontmatter=None)
    assert result.archetype == "none"


def test_detect_no_companion_when_only_storyline(tmp_path: Path):
    """Storyline but NO characters → archetype=none."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "storyline_dsl.py").write_text(
        "# storyline things\n", encoding="utf-8"
    )

    result = detect_companion_archetype(repo_root=tmp_path, hub_frontmatter=None)
    assert result.archetype == "none"
