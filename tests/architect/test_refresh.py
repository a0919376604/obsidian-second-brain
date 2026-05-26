from pathlib import Path

import pytest

from scripts.architect.refresh import RefreshAction, decide_module_refresh


def test_new_module_regenerates(single_lang_python: Path):
    action = decide_module_refresh(
        module={"slug": "newmod", "paths": ["src/newmod/"]},
        lockfile_modules={},
        old_commit=None,
        new_commit="abc",
        repo_root=single_lang_python,
        force=False,
    )
    assert action == RefreshAction.GENERATE


def test_path_change_regenerates(single_lang_python: Path):
    action = decide_module_refresh(
        module={"slug": "auth", "paths": ["src/auth-new/"]},
        lockfile_modules={"auth": {"paths": ["src/auth/"]}},
        old_commit="abc",
        new_commit="def",
        repo_root=single_lang_python,
        force=False,
    )
    assert action == RefreshAction.REGENERATE


def test_force_always_regenerates(single_lang_python: Path):
    action = decide_module_refresh(
        module={"slug": "auth", "paths": ["src/auth/"]},
        lockfile_modules={"auth": {"paths": ["src/auth/"]}},
        old_commit="abc",
        new_commit="abc",
        repo_root=single_lang_python,
        force=True,
    )
    assert action == RefreshAction.REGENERATE


def test_unchanged_module_skips(single_lang_python: Path):
    # Same commit, same paths, no force: skip.
    action = decide_module_refresh(
        module={"slug": "auth", "paths": ["src/auth/"]},
        lockfile_modules={"auth": {"paths": ["src/auth/"]}},
        old_commit="abc",
        new_commit="abc",
        repo_root=single_lang_python,
        force=False,
    )
    assert action == RefreshAction.SKIP
