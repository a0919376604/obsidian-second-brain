from pathlib import Path

from scripts.architect.api_surface import detect_api_surface


def test_python_argparse_cli(tmp_path: Path):
    (tmp_path / "cli.py").write_text(
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "sub = p.add_subparsers()\n"
        "foo = sub.add_parser('foo', help='do foo')\n"
        "bar = sub.add_parser('bar', help='do bar')\n"
    )
    surf = detect_api_surface(tmp_path)
    cmds = {c.name for c in surf.cli_commands}
    assert "foo" in cmds
    assert "bar" in cmds


def test_fastapi_routes(tmp_path: Path):
    (tmp_path / "routes.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/items/{id}')\n"
        "def get_item(id: int): ...\n"
        "@app.post('/items')\n"
        "def create_item(): ...\n"
    )
    surf = detect_api_surface(tmp_path)
    assert any(r.method == "GET" and r.path == "/items/{id}" for r in surf.http_routes)
    assert any(r.method == "POST" and r.path == "/items" for r in surf.http_routes)


def test_python_all_exports(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text(
        '__all__ = ["login", "logout"]\n'
        'def login(): pass\n'
        'def logout(): pass\n'
        'def _internal(): pass\n'
    )
    surf = detect_api_surface(tmp_path)
    names = {e.symbol for e in surf.exports}
    assert "login" in names
    assert "logout" in names
    assert "_internal" not in names


def test_env_var_detection_python(tmp_path: Path):
    (tmp_path / "config.py").write_text(
        "import os\n"
        "DB_URL = os.getenv('DATABASE_URL', 'sqlite:///dev.db')\n"
        "API_KEY = os.environ['API_KEY']\n"
    )
    surf = detect_api_surface(tmp_path)
    vars_seen = {v.name for v in surf.env_vars}
    assert "DATABASE_URL" in vars_seen
    assert "API_KEY" in vars_seen
    db = next(v for v in surf.env_vars if v.name == "DATABASE_URL")
    assert db.default == "sqlite:///dev.db"


def test_empty_project_returns_detection_status_none(tmp_path: Path):
    surf = detect_api_surface(tmp_path)
    assert surf.detection_status == "none"
    assert surf.cli_commands == []
    assert surf.http_routes == []
