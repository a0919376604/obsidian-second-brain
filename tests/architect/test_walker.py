from pathlib import Path

from scripts.architect.walker import walk_repo


def test_walk_repo_returns_relative_paths(single_lang_python: Path):
    files = walk_repo(single_lang_python)
    assert "pyproject.toml" in files
    assert "src/auth/login.py" in files
    assert "tests/test_login.py" in files


def test_walk_repo_excludes_gitignored(single_lang_python: Path, tmp_path: Path):
    # Create a __pycache__/ in the fixture to verify it's filtered.
    cache = single_lang_python / "__pycache__"
    cache.mkdir(exist_ok=True)
    (cache / "junk.pyc").touch()
    try:
        files = walk_repo(single_lang_python)
        assert not any("__pycache__" in f for f in files)
    finally:
        # Clean up so the fixture is not polluted.
        (cache / "junk.pyc").unlink()
        cache.rmdir()


def test_walk_repo_skips_binary_and_dot_git(single_lang_python: Path):
    files = walk_repo(single_lang_python)
    assert not any(f.startswith(".git/") for f in files)
