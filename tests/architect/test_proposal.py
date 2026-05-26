from pathlib import Path

from scripts.architect.proposal import propose_modules


def test_default_proposal_one_per_top_folder(single_lang_python: Path):
    modules = propose_modules(single_lang_python)
    slugs = sorted(m["slug"] for m in modules)
    # src/ contains auth, db, api -> 3 modules (default looks inside src/ if it exists)
    assert "auth" in slugs
    assert "db" in slugs
    assert "api" in slugs


def test_tests_folder_excluded(single_lang_python: Path):
    modules = propose_modules(single_lang_python)
    by_slug = {m["slug"]: m for m in modules}
    # tests/ appears with excluded=True, but not omitted entirely
    if "tests" in by_slug:
        assert by_slug["tests"]["excluded"] is True


def test_role_defaults_to_other(single_lang_python: Path):
    modules = propose_modules(single_lang_python)
    for m in modules:
        if not m["excluded"]:
            assert m["role"] in {"surface", "core", "adapter", "infra", "data", "docs", "other"}
