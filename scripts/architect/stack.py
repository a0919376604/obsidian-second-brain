"""Best-effort stack detection from package manifests and root config files.

Returns a dict suitable for the overview frontmatter `stack:` block. Only
populates fields the detector can confidently fill; uncertain fields are
omitted (NEVER guessed).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Map of dependency-name (lowercase) -> human framework label.
_FRAMEWORK_MAP = {
    # Python.
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "starlette": "Starlette",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "celery": "Celery",
    "click": "Click",
    "typer": "Typer",
    # JS/TS.
    "next": "Next.js",
    "react": "React",
    "vue": "Vue",
    "svelte": "Svelte",
    "express": "Express",
    "fastify": "Fastify",
    "@prisma/client": "Prisma",
    "prisma": "Prisma",
    "@trpc/server": "tRPC",
    "drizzle-orm": "Drizzle",
    # Go.
    "github.com/gin-gonic/gin": "Gin",
    "github.com/labstack/echo": "Echo",
}

_TEST_MAP_PY = {"pytest": "pytest", "unittest": "unittest"}
_TEST_MAP_JS = {"vitest": "vitest", "jest": "jest", "mocha": "mocha", "playwright": "playwright"}


def detect_stack(repo_root: Path) -> dict:
    """Return a dict ready to drop into overview frontmatter as `stack: {...}`."""
    repo_root = repo_root.resolve()
    stack: dict = {}
    py = _from_pyproject(repo_root)
    js = _from_package_json(repo_root)
    if (repo_root / "pyproject.toml").exists():
        stack["primary-language"] = "Python"
        stack.update(py)
    elif (repo_root / "package.json").exists():
        stack["primary-language"] = "TypeScript or JavaScript"
        stack.update(js)
    elif (repo_root / "Cargo.toml").exists():
        stack["primary-language"] = "Rust"
    elif (repo_root / "go.mod").exists():
        stack["primary-language"] = "Go"
    # Build tools.
    if (repo_root / "turbo.json").exists():
        stack.setdefault("build", "")
        stack["build"] = (stack.get("build") + " + turbo").strip(" +")
    return stack


def _from_pyproject(repo_root: Path) -> dict:
    p = repo_root / "pyproject.toml"
    if not p.exists():
        return {}
    data = tomllib.loads(p.read_text())
    deps = data.get("project", {}).get("dependencies", []) or []
    dev_deps = (
        data.get("dependency-groups", {}).get("dev", [])
        or data.get("tool", {}).get("poetry", {}).get("group", {}).get("dev", {}).get("dependencies", {})
        or []
    )
    out: dict = {}
    fws = sorted({_FRAMEWORK_MAP[_dep_name(d).lower()] for d in deps if _dep_name(d).lower() in _FRAMEWORK_MAP})
    if fws:
        out["frameworks"] = fws
    test_candidates = list(deps) + list(dev_deps if isinstance(dev_deps, list) else dev_deps.keys() if isinstance(dev_deps, dict) else [])
    for t in test_candidates:
        name = _dep_name(t).lower()
        if name in _TEST_MAP_PY:
            out["test"] = _TEST_MAP_PY[name]
            break
    if "tool" in data and "pytest" in data.get("tool", {}):
        out["test"] = "pytest"
    return out


def _from_package_json(repo_root: Path) -> dict:
    p = repo_root / "package.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    deps = list((data.get("dependencies") or {}).keys()) + list((data.get("devDependencies") or {}).keys())
    out: dict = {}
    fws = sorted({_FRAMEWORK_MAP[d.lower()] for d in deps if d.lower() in _FRAMEWORK_MAP})
    if fws:
        out["frameworks"] = fws
    for d in deps:
        if d.lower() in _TEST_MAP_JS:
            out["test"] = _TEST_MAP_JS[d.lower()]
            break
    pkg_mgr = "npm"
    if (repo_root / "pnpm-lock.yaml").exists():
        pkg_mgr = "pnpm"
    elif (repo_root / "yarn.lock").exists():
        pkg_mgr = "yarn"
    out["build"] = pkg_mgr
    return out


_DEP_NAME_RE = re.compile(r"^([A-Za-z0-9._@/+-]+)")


def _dep_name(spec: str) -> str:
    """Extract the bare package name from a dep spec like 'fastapi>=0.110'."""
    m = _DEP_NAME_RE.match(spec)
    return m.group(1) if m else spec
