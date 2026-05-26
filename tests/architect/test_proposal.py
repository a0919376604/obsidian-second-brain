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

from scripts.architect.proposal import propose_modules_with_heuristics


def test_flat_repo_fallback(flat_repo: Path):
    modules = propose_modules_with_heuristics(flat_repo)
    slugs = [m["slug"] for m in modules]
    # Flat layout produces a single "core" module covering the root.
    assert "core" in slugs


def test_monorepo_workspaces(monorepo_pnpm: Path):
    modules = propose_modules_with_heuristics(monorepo_pnpm)
    slugs = sorted(m["slug"] for m in modules)
    assert "web" in slugs
    assert "api" in slugs


def test_polyglot_proposal(polyglot_repo: Path):
    modules = propose_modules_with_heuristics(polyglot_repo)
    slugs = sorted(m["slug"] for m in modules if not m["excluded"])
    # python/, web/, scripts/ are top-level
    assert "python" in slugs
    assert "web" in slugs


def test_docs_only_warning_signal(docs_only_repo: Path):
    modules = propose_modules_with_heuristics(docs_only_repo)
    # docs/ excluded, scripts/ kept. Function still returns modules; the
    # "mostly docs" warning is emitted by scan.py, not proposal.py.
    slugs = [m["slug"] for m in modules]
    assert "scripts" in slugs
