from pathlib import Path

from scripts.architect.readme import extract_sections

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "readmes"


def test_extract_known_sections_from_full_readme():
    text = (FIXTURE_DIR / "full.md").read_text()
    sections = extract_sections(text)
    assert "Features" in sections
    assert "Fast HTTP client" in sections["Features"]
    assert "Roadmap" in sections
    assert "v2: streaming support" in sections["Roadmap"]
    assert "Coming Soon" in sections
    assert "gRPC adapter" in sections["Coming Soon"]
    assert "Limitations" in sections
    assert "No Windows support" in sections["Limitations"]
    assert "Known Issues" in sections
    assert "Future Work" in sections


def test_empty_readme_returns_empty_dict():
    text = (FIXTURE_DIR / "empty.md").read_text()
    assert extract_sections(text) == {}


def test_section_extraction_is_case_insensitive():
    text = "# Foo\n\n## FEATURES\n\n- one\n\n## roadmap\n\n- two\n"
    sections = extract_sections(text)
    assert "Features" in sections  # normalized to title-case key
    assert "Roadmap" in sections


def test_section_body_excludes_subsequent_h2():
    text = "## Features\n\n- a\n\n## Roadmap\n\n- b\n"
    sections = extract_sections(text)
    assert "Roadmap" not in sections["Features"]
    assert "- a" in sections["Features"]
