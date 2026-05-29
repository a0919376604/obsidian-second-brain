"""Tests for /obsidian-brainstorm section registration + helpers."""
from __future__ import annotations

from scripts.architect.sections import SECTION_TYPES, _BLOCK_NAMES, _BLOCK_HEADINGS


def test_brainstorm_section_type_present():
    assert SECTION_TYPES["brainstorm"] == "project-brainstorm"


def test_brainstorm_block_names_v1():
    expected = (
        "context",
        "opening-provocations",
        "drilled-explorations",
        "distilled-imps",
        "hypotheses",
        "parked",
        "open-questions",
        "meta-reflection",
        "dependencies",
    )
    assert _BLOCK_NAMES["brainstorm"] == expected


def test_brainstorm_block_headings_registered():
    """All v1 brainstorm block names must have entries in _BLOCK_HEADINGS."""
    new_blocks = [
        "context",
        "opening-provocations",
        "drilled-explorations",
        "distilled-imps",
        "hypotheses",
        "parked",
        "open-questions",
        "meta-reflection",
    ]
    for block in new_blocks:
        assert block in _BLOCK_HEADINGS, f"missing heading for {block}"
    # `dependencies` block reuses existing v3 mapping ("## Dependencies and consumers").
    assert "dependencies" in _BLOCK_HEADINGS


def test_parse_hypothesis_block_extracts_fields():
    """Hypothesis block has H3 entries with fields:
    假設 / 驗證方式 / kill criterion / owner / status."""
    from scripts.architect.sections import parse_hypothesis_block

    body = (
        "### H1: 客服自助 Rich Menu 能降 ticket 量 30%\n"
        "- **假設:** LINE Rich Menu 加 5 個自助 FAQ 入口後,客服 ticket 量在 4 週內降 ≥ 30%\n"
        "- **驗證方式:** 灰度部署到 20% 用戶,4 週後比較對照組 ticket 量\n"
        "- **kill criterion:** 降幅 < 10% 或客戶滿意度同步下降\n"
        "- **owner:** [[people/客服 lead]]\n"
        "- **status:** unvalidated\n"
        "\n"
        "### H2: 統一 embedding provider 後 recall 提升\n"
        "- **假設:** write+read 用同 embedding provider 後,golden-set recall@5 提升 ≥ 15%\n"
        "- **驗證方式:** 跑 evaluation/retrieval golden-set 對比\n"
        "- **kill criterion:** recall@5 變化 < 5%\n"
        "- **owner:** [[people/AI lead]]\n"
        "- **status:** unvalidated\n"
    )
    hyps = parse_hypothesis_block(body)
    assert len(hyps) == 2
    h1 = hyps[0]
    assert h1["title"] == "H1: 客服自助 Rich Menu 能降 ticket 量 30%"
    assert "LINE Rich Menu" in h1["assumption"]
    assert "灰度部署到 20%" in h1["validation"]
    assert "降幅 < 10%" in h1["kill_criterion"]
    assert "客服 lead" in h1["owner"]
    assert h1["status"] == "unvalidated"


def test_parse_hypothesis_block_ignores_entries_missing_required_fields():
    """An H3 missing assumption / validation / kill_criterion is dropped."""
    from scripts.architect.sections import parse_hypothesis_block

    body = (
        "### H1: incomplete (no fields)\n"
        "Just prose, no bullets.\n"
        "\n"
        "### H2: complete\n"
        "- **假設:** A\n"
        "- **驗證方式:** B\n"
        "- **kill criterion:** C\n"
        "- **owner:** D\n"
        "- **status:** unvalidated\n"
    )
    hyps = parse_hypothesis_block(body)
    assert len(hyps) == 1
    assert hyps[0]["title"] == "H2: complete"


def test_parse_hypothesis_block_returns_empty_when_no_h3():
    from scripts.architect.sections import parse_hypothesis_block
    assert parse_hypothesis_block("just paragraph text\nno h3 headings") == []
