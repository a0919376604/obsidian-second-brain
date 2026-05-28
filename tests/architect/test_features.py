"""v4.2 features.md tests."""
from __future__ import annotations

from scripts.architect.sections import (
    DEPRECATED_SECTIONS,
    SECTION_TYPES,
    _BLOCK_HEADINGS,
    _BLOCK_NAMES,
)


def test_features_section_not_deprecated_in_v4_2():
    """v4.2 un-deprecates features. compose_note(section='features') should NOT
    log a deprecation warning."""
    assert "features" not in DEPRECATED_SECTIONS, (
        "features must be removed from DEPRECATED_SECTIONS in v4.2"
    )


def test_features_section_type_present():
    assert SECTION_TYPES["features"] == "architecture-features"


def test_features_v4_2_block_names():
    """v4.2 features has 10 @generated blocks in a specific order."""
    expected = (
        "summary",
        "capability-inventory",
        "product-coverage",
        "limitations",
        "strengths",
        "weaknesses",
        "missing-features",
        "improvements",
        "doc-sync-actions",
        "dependencies",
    )
    assert _BLOCK_NAMES["features"] == expected


def test_features_v4_2_block_headings_present():
    """Every block name in features has a heading in _BLOCK_HEADINGS."""
    for block_name in _BLOCK_NAMES["features"]:
        assert block_name in _BLOCK_HEADINGS, f"missing heading for {block_name}"


def test_features_new_block_headings_text():
    """v4.2 introduces 4 new block headings not used elsewhere."""
    assert _BLOCK_HEADINGS["capability-inventory"] == "## Capability inventory"
    assert _BLOCK_HEADINGS["product-coverage"] == "## Product coverage"
    assert _BLOCK_HEADINGS["limitations"] == "## Limitations"
    assert _BLOCK_HEADINGS["missing-features"] == "## Missing features"
    assert _BLOCK_HEADINGS["doc-sync-actions"] == "## Doc sync actions"


def test_scan_report_includes_agents_md_text(tmp_path):
    """build_scan_report exposes raw AGENTS.md text (capped 20KB)."""
    from scripts.architect.scan import build_scan_report

    (tmp_path / "AGENTS.md").write_text("# Agents\nLine 1\nLine 2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# R", encoding="utf-8")
    report = build_scan_report(tmp_path, vault_project_dir=None)
    assert "agents_md_text" in report
    assert "Agents" in report["agents_md_text"]
    assert len(report["agents_md_text"]) <= 20_000


def test_scan_report_research_excerpts_when_vault_project_dir_passed(tmp_path):
    """When --vault-project-dir given, scan walks Research/ for excerpts."""
    from scripts.architect.scan import build_scan_report

    (tmp_path / "AGENTS.md").write_text("a\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("r\n", encoding="utf-8")
    vault_proj = tmp_path / "vault_proj"
    research = vault_proj / "Research"
    research.mkdir(parents=True)
    (research / "X.md").write_text(
        "---\ntitle: X\ndate: 2026-05-01\ntags: []\n---\n\nResearch para.\n",
        encoding="utf-8",
    )
    report = build_scan_report(tmp_path, vault_project_dir=vault_proj)
    excerpts = report["research_excerpts"]
    assert len(excerpts) == 1
    assert excerpts[0]["title"] == "X"


def test_scan_report_research_excerpts_empty_when_dir_missing(tmp_path):
    """When --vault-project-dir not passed, research_excerpts = []."""
    from scripts.architect.scan import build_scan_report

    (tmp_path / "AGENTS.md").write_text("a\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("r\n", encoding="utf-8")
    report = build_scan_report(tmp_path, vault_project_dir=None)
    assert report["research_excerpts"] == []


def test_scan_report_git_last_touch_keyed_by_path(tmp_path):
    """build_scan_report adds git_last_touch dict for api_surface files."""
    import subprocess
    from scripts.architect.scan import build_scan_report

    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("r\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("a\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("def hello(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init", "--date", "2026-05-15T00:00:00"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env={**__import__("os").environ,
             "GIT_AUTHOR_DATE": "2026-05-15T00:00:00",
             "GIT_COMMITTER_DATE": "2026-05-15T00:00:00"},
    )

    report = build_scan_report(tmp_path, vault_project_dir=None)
    assert "git_last_touch" in report
    # main.py was committed → must have a date.
    assert report["git_last_touch"].get("main.py") == "2026-05-15"
