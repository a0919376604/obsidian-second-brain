from pathlib import Path

from scripts.architect.stack import detect_stack


def test_python_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\n'
        'name = "x"\n'
        'dependencies = ["fastapi>=0.110", "sqlalchemy>=2.0"]\n'
        '[tool.pytest.ini_options]\n'
        'testpaths = ["tests"]\n'
    )
    stack = detect_stack(tmp_path)
    assert stack["primary-language"] == "Python"
    assert "FastAPI" in stack["frameworks"]
    assert "SQLAlchemy" in stack["frameworks"]
    assert stack["test"] == "pytest"


def test_typescript_nextjs(tmp_path: Path):
    (tmp_path / "package.json").write_text(
        '{"name":"x","dependencies":{"next":"14.0.0","react":"18.0.0",'
        '"@prisma/client":"5.0.0"},"devDependencies":{"vitest":"1.0.0"}}'
    )
    (tmp_path / "next.config.js").write_text("module.exports = {};\n")
    stack = detect_stack(tmp_path)
    assert stack["primary-language"] == "TypeScript or JavaScript"
    assert "Next.js" in stack["frameworks"]
    assert "Prisma" in stack["frameworks"]
    assert stack["test"] == "vitest"


def test_returns_empty_when_no_config(tmp_path: Path):
    assert detect_stack(tmp_path) == {}


def test_unrecognized_deps_are_dropped(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["some-random-lib"]\n'
    )
    stack = detect_stack(tmp_path)
    # primary-language is keyed off pyproject existence, so still present.
    assert stack.get("primary-language") == "Python"
    # No frameworks line in output because nothing recognized.
    assert "frameworks" not in stack or stack["frameworks"] == []
