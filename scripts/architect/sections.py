"""Section synthesis: signal collection, prompt building, note composition.

Each of the 5 narrative sections has its own signal subset. The signal subset
is hashed for refresh comparison. The composed note wraps LLM-generated body
in @generated sentinels and frontmatter.

LLM call itself happens in the slash command body (the agent). This module
provides pure helpers that the agent invokes for context and for writing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from scripts.architect.lang import heading

SECTION_NAMES = ("api-surface", "features", "decisions", "roadmap", "future")

# Section -> note filename (under Projects/<P>/Architecture/).
SECTION_FILENAMES = {
    "api-surface": "api-surface.md",
    "features": "features.md",
    "decisions": "decisions.md",
    "roadmap": "roadmap.md",
    "future": "future.md",
}

# Section -> frontmatter `type:` value.
SECTION_TYPES = {
    "api-surface": "architecture-api-surface",
    "features": "architecture-features",
    "decisions": "architecture-decisions",
    "roadmap": "architecture-roadmap",
    "future": "architecture-future",
}


def signal_hash(signal: dict) -> str:
    """Stable SHA-256 hash of a JSON-serializable signal dict."""
    canonical = json.dumps(signal, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def collect_signals(section: str, scan_report: dict, manifest_modules: list[dict]) -> dict:
    """Return the signal subset relevant to one section.

    Includes everything the LLM needs as context and everything that, if
    changed, should trigger regeneration.
    """
    if section not in SECTION_NAMES:
        raise ValueError(f"unknown section: {section}")
    readme = scan_report.get("readme_sections", {})
    cl = scan_report.get("changelog", {})
    todos = scan_report.get("todos", {})
    api = scan_report.get("api_surface", {})
    decision_docs = scan_report.get("decision_docs", [])
    stack = scan_report.get("stack", {})

    if section == "api-surface":
        return {
            "cli_commands": api.get("cli_commands", []),
            "http_routes": api.get("http_routes", []),
            "exports": api.get("exports", []),
            "env_vars": api.get("env_vars", []),
            "detection_status": api.get("detection_status", "none"),
        }
    if section == "features":
        return {
            "readme_features": readme.get("Features", ""),
            "cli_commands": api.get("cli_commands", []),
            "http_routes": api.get("http_routes", []),
            "modules": [{"slug": m["slug"], "description": m.get("description", ""), "paths": m.get("paths", [])} for m in manifest_modules],
        }
    if section == "decisions":
        return {
            "decision_docs": decision_docs,
            "stack": stack,
            "external_deps": scan_report.get("external_deps", []),
            "commit_message_decisions": scan_report.get("commit_decisions", []),
            "pattern_decisions": scan_report.get("pattern_decisions", []),
        }
    if section == "roadmap":
        roadmap_todos = []
        for slug, items in todos.items():
            if slug == "_unmapped":
                continue
            for t in items:
                if (t.get("label") or "").lower() in ("roadmap", "next", "plan"):
                    roadmap_todos.append({**t, "module": slug})
        return {
            "readme_roadmap": readme.get("Roadmap", "") or readme.get("Coming Soon", ""),
            "changelog_unreleased": cl.get("unreleased"),
            "changelog_recent": cl.get("recent_versions", []),
            "roadmap_todos": roadmap_todos,
        }
    if section == "future":
        future_todos = []
        for slug, items in todos.items():
            for t in items:
                if (t.get("label") or "").lower() in ("future", "idea", "someday"):
                    future_todos.append({**t, "module": slug})
        return {
            "readme_limitations": readme.get("Limitations", ""),
            "readme_known_issues": readme.get("Known Issues", ""),
            "readme_future_work": readme.get("Future Work", ""),
            "future_todos": future_todos,
            "truncated_modules": [m["slug"] for m in manifest_modules if m.get("scan_truncated")],
        }
    raise AssertionError("unreachable")  # pragma: no cover


_PROMPT_LANG_RULES_EN = (
    "Write the body in English. Preserve verbatim: file paths, function names, "
    "class names, variable names, CLI command strings, URLs."
)
_PROMPT_LANG_RULES_ZH = (
    "請以繁體中文 (Traditional Chinese, zh-TW) 撰寫散文與 heading。"
    "以下元素必須原樣保留英文 (code identifier / 機讀符號):"
    "檔案路徑、變數名、函式名、類別名、import path、CLI 命令字串、URL、"
    "frontmatter key、enum 值、wikilink 內的檔名段。"
    "範例:\n"
    "  ✅ 從 `src/cli.py:42` 的 `argparse` 解析器推論而來\n"
    "  ❌ From src/cli.py:42's argparse parser inferred\n"
    "  ❌ 從來源/cli.py:42 的 引數解析器 推論而來"
)

# Required @generated block names per section (preamble + body composition).
_BLOCK_NAMES = {
    "api-surface": ("summary", "cli-commands", "http-routes", "exports", "env-vars"),
    "features": ("summary", "capability-map", "notable-details"),
    "decisions": ("summary", "stack-rationale", "detected-adrs", "pattern-decisions",
                  "commit-message-decisions", "promote-to-adr"),
    "roadmap": ("summary", "near-term", "trajectory", "todo-clusters", "signals-reviewed"),
    "future": ("summary", "known-limitations", "gap-analysis", "aspirational-ideas"),
}


def build_prompt(section: str, signal: dict, output_lang: str, project: str) -> str:
    """Render the LLM prompt for a section synthesis."""
    rules = _PROMPT_LANG_RULES_ZH if output_lang == "zh-TW" else _PROMPT_LANG_RULES_EN
    blocks = _BLOCK_NAMES[section]
    lines = [
        f"You are synthesizing the `{section}` note for project `{project}`.",
        f"Output language: {output_lang}.",
        rules,
        "",
        "Produce one @generated block per name below. Each block body is the "
        "raw markdown text (no sentinel tags — those are added by the caller).",
        "Return JSON: {\"<block-name>\": \"<markdown body>\"}.",
        f"Required blocks: {list(blocks)}.",
        "",
        "Signal:",
        json.dumps(signal, indent=2, ensure_ascii=False, default=str),
    ]
    return "\n".join(lines)


def compose_note(
    *,
    section: str,
    project: str,
    repo_label: str,
    commit: str,
    signal_sources: list[str],
    confidence: str,
    output_lang: str,
    generated_blocks: dict[str, str],
    status: str = "current",
) -> str:
    """Assemble the final note markdown from LLM-generated blocks + metadata."""
    today = date.today().isoformat()
    type_value = SECTION_TYPES[section]
    tag_suffix = section.replace("-", "-")  # keep stable; e.g. "api-surface"
    fm_lines = [
        "---",
        f"type: {type_value}",
        f"date: {today}",
        f'project: "[[{project}]]"',
        f"repo: {repo_label}",
        f"last-scanned: {today}",
        f"commit: {commit}",
        f"sources: {json.dumps(signal_sources)}",
        f"confidence: {confidence}",
        f"lang: {output_lang}",
        f"tags: [architecture, {tag_suffix}]",
        "ai-first: true",
        f"status: {status}",
    ]
    if section == "api-surface":
        # detection-status hints at scanner confidence in the table contents.
        detection_status = "complete" if generated_blocks else "none"
        fm_lines.append(f"detection-status: {detection_status}")
    fm_lines.append("---")

    body_parts = [
        "",
        heading("## For future Claude", output_lang),
        _preamble_for(section, output_lang),
        "",
    ]
    for name in _BLOCK_NAMES[section]:
        body = generated_blocks.get(name, "").strip()
        if not body:
            continue
        body_parts.append(f"<!-- @generated:start {name} -->")
        body_parts.append(body)
        body_parts.append(f"<!-- @generated:end {name} -->")
        body_parts.append("")
    body_parts.append(heading("## Related", output_lang))
    body_parts.append(f"- [[Architecture/overview]]")
    body_parts.append(f"- [[{project}]]")
    return "\n".join(fm_lines + body_parts) + "\n"


def _preamble_for(section: str, lang: str) -> str:
    """Short preamble describing the note's purpose to future-Claude."""
    if lang == "zh-TW":
        return {
            "api-surface": "本檔是 API 介面參考表。要查命令或 endpoint 就看這裡。",
            "features": "本檔列出本 codebase 對使用者提供的能力。具體 CLI/HTTP 表在 [[Architecture/api-surface]],模組層級在 [[Architecture/modules]]。",
            "decisions": "本檔是關鍵技術決定的索引;真正的 ADR 應該透過 /obsidian-adr 升級到 Decisions/。",
            "roadmap": "本檔合成自 CHANGELOG、README、TODO 群組。標明來源,推論值低信心。",
            "future": "本檔是 gap 分析與北極星想法。多為推論,非已決方向。",
        }[section]
    return {
        "api-surface": "This is the API surface reference. Look up commands or endpoints here.",
        "features": "Capabilities exposed by this codebase. See [[Architecture/api-surface]] for the structured tables and [[Architecture/modules]] for per-module depth.",
        "decisions": "Index of key technical decisions. Promote individual entries to full ADRs via /obsidian-adr into Decisions/.",
        "roadmap": "Synthesized from CHANGELOG, README, and TODO clusters. Inference is marked.",
        "future": "Gap analysis and north-star ideas. Mostly inferred, not committed.",
    }[section]


def module_for_path(rel_path: str, manifest_modules: list[dict]) -> str | None:
    """Return the slug of the module containing `rel_path`, or None."""
    src = rel_path.split(":")[0]
    for m in manifest_modules:
        for prefix in m.get("paths", []):
            if src == prefix or src.startswith(prefix.rstrip("/") + "/"):
                return m["slug"]
    return None
