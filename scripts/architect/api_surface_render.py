"""Deterministic markdown table renderers for api-surface.md sections.

These do not call an LLM. They turn scanner output into structured tables.
"""

from __future__ import annotations


_HEADERS = {
    "cli": {
        "en": ("Command", "Description", "Source", "Module"),
        "zh-TW": ("指令", "說明", "來源", "模組"),
    },
    "http": {
        "en": ("Method", "Path", "Handler", "Module"),
        "zh-TW": ("方法", "路徑", "Handler", "模組"),
    },
    "exports": {
        "en": ("Symbol", "Kind", "Source", "Module"),
        "zh-TW": ("符號", "種類", "來源", "模組"),
    },
    "env": {
        "en": ("Var", "Required", "Default", "Source"),
        "zh-TW": ("變數", "必填", "預設值", "來源"),
    },
}


def _table(headers: tuple[str, ...], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join([head, sep, body])


def render_cli_table(rows: list[dict], lang: str) -> str:
    if not rows:
        return ""
    h = _HEADERS["cli"][lang]
    body = [[f"`{r['name']}`", r.get("description", ""), f"`{r['source']}`",
             f"[[modules/{r.get('module', '')}]]" if r.get("module") else ""] for r in rows]
    return _table(h, body)


def render_http_table(rows: list[dict], lang: str) -> str:
    if not rows:
        return ""
    h = _HEADERS["http"][lang]
    body = [[r["method"], f"`{r['path']}`", f"`{r['handler']}`",
             f"[[modules/{r.get('module', '')}]]" if r.get("module") else ""] for r in rows]
    return _table(h, body)


def render_exports_table(rows: list[dict], lang: str) -> str:
    if not rows:
        return ""
    h = _HEADERS["exports"][lang]
    body = [[f"`{r['symbol']}`", r.get("kind", ""), f"`{r['source']}`",
             f"[[modules/{r.get('module', '')}]]" if r.get("module") else ""] for r in rows]
    return _table(h, body)


def render_env_table(rows: list[dict], lang: str) -> str:
    if not rows:
        return ""
    h = _HEADERS["env"][lang]
    yes_no = ("yes" if lang == "en" else "是", "no" if lang == "en" else "否")
    body = []
    for r in rows:
        body.append([
            f"`{r['name']}`",
            yes_no[0] if r.get("required") else yes_no[1],
            f"`{r['default']}`" if r.get("default") is not None else "",
            f"`{r['source']}`",
        ])
    return _table(h, body)
