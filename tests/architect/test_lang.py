from pathlib import Path

from scripts.architect.lang import resolve_output_lang


def test_cli_flag_wins(tmp_path: Path):
    (tmp_path / "_CLAUDE.md").write_text("- output-lang: en\n")
    assert resolve_output_lang(cli_flag="zh-TW", vault_root=tmp_path) == "zh-TW"


def test_claude_md_when_no_flag(tmp_path: Path):
    (tmp_path / "_CLAUDE.md").write_text("Some prelude.\n- output-lang: zh-TW\nMore.\n")
    assert resolve_output_lang(cli_flag=None, vault_root=tmp_path) == "zh-TW"


def test_default_en_when_no_signal(tmp_path: Path):
    assert resolve_output_lang(cli_flag=None, vault_root=tmp_path) == "en"


def test_invalid_lang_falls_back_to_en(tmp_path: Path):
    (tmp_path / "_CLAUDE.md").write_text("- output-lang: klingon\n")
    assert resolve_output_lang(cli_flag=None, vault_root=tmp_path) == "en"


def test_supported_langs_constant():
    from scripts.architect.lang import SUPPORTED_LANGS
    assert set(SUPPORTED_LANGS) == {"en", "zh-TW"}


def test_heading_returns_zh_for_known_key():
    from scripts.architect.lang import heading
    assert heading("## Summary", "zh-TW") == "## 摘要"
    assert heading("## CLI commands", "zh-TW") == "## CLI 命令"


def test_heading_returns_en_for_en_lang():
    from scripts.architect.lang import heading
    assert heading("## Summary", "en") == "## Summary"


def test_heading_passes_through_unknown_key():
    from scripts.architect.lang import heading
    assert heading("## Unknown thing", "zh-TW") == "## Unknown thing"


def test_heading_map_covers_all_required_keys():
    from scripts.architect.lang import HEADING_MAP
    required = {
        "## For future Claude", "## Summary", "## Related",
        "## Purpose", "## Stack", "## Capability MOC", "## Structure MOC",
        "## API surface", "## Layer map", "## External dependencies", "## Key abstractions",
        "## Capability map", "## Notable details",
        "## Near term", "## Trajectory", "## TODO clusters", "## Signals reviewed",
        "## Stack rationale", "## Detected ADRs", "## Pattern decisions",
        "## Commit-message decisions", "## Promote to ADR",
        "## Known limitations", "## Gap analysis", "## Aspirational ideas",
        "## CLI commands", "## HTTP routes", "## Public exports", "## Environment variables",
        "## What it does", "## How it works", "## Key files", "## Depends on",
        "## Consumed by", "## Recent activity",
        "## Signature", "## Inputs and outputs", "## Behavior notes", "## Callers",
    }
    missing = required - set(HEADING_MAP.keys())
    assert not missing, f"missing heading keys: {missing}"
