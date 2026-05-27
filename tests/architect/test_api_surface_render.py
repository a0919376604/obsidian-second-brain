from scripts.architect.api_surface_render import (
    render_cli_table, render_http_table, render_exports_table, render_env_table,
)


def test_cli_table_en():
    rows = [{"name": "foo", "description": "do foo", "source": "src/cli.py:1", "module": "cli"}]
    table = render_cli_table(rows, lang="en")
    assert "| Command | Description | Source | Module |" in table
    assert "| `foo` | do foo | `src/cli.py:1` | [[modules/cli]] |" in table


def test_cli_table_zh():
    rows = [{"name": "foo", "description": "做 foo", "source": "src/cli.py:1", "module": "cli"}]
    table = render_cli_table(rows, lang="zh-TW")
    assert "| 指令 | 說明 | 來源 | 模組 |" in table


def test_empty_table_returns_empty_string():
    assert render_cli_table([], lang="en") == ""
    assert render_http_table([], lang="en") == ""


def test_http_table():
    rows = [{"method": "GET", "path": "/x", "handler": "get_x", "source": "src/api.py:5", "module": "api"}]
    table = render_http_table(rows, lang="en")
    assert "| Method | Path | Handler | Module |" in table
    assert "GET" in table and "`/x`" in table


def test_env_table_marks_required():
    rows = [
        {"name": "API_KEY", "required": True, "default": None, "source": "src/c.py:1", "used_by": "api"},
        {"name": "DB_URL", "required": False, "default": "sqlite://", "source": "src/c.py:2", "used_by": "db"},
    ]
    table = render_env_table(rows, lang="en")
    assert "API_KEY" in table and "yes" in table
    assert "DB_URL" in table and "sqlite://" in table
