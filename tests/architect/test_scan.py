from pathlib import Path

from scripts.architect.scan import run_phase_one, ScanResult


def test_phase_one_produces_manifest_and_report(single_lang_python: Path):
    result: ScanResult = run_phase_one(single_lang_python)
    assert result.manifest.version == 1
    assert len(result.manifest.modules) >= 3  # auth, db, api
    assert result.manifest.last_scan["commit"]  # has commit hash
    assert "files" in result.scan_report
    assert "languages" in result.scan_report
    assert "entry_points" in result.scan_report
    assert "external_deps" in result.scan_report


def test_phase_one_deterministic(single_lang_python: Path):
    r1 = run_phase_one(single_lang_python)
    r2 = run_phase_one(single_lang_python)
    # Same commit + same scanner version -> same manifest.
    assert r1.manifest.last_scan["commit"] == r2.manifest.last_scan["commit"]
    assert [m["slug"] for m in r1.manifest.modules] == [m["slug"] for m in r2.manifest.modules]
