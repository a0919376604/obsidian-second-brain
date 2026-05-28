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
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scripts.architect.lang import heading

_logger = logging.getLogger(__name__)

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
    "overview": "architecture-overview",
    "api-surface": "architecture-api-surface",
    "features": "architecture-features",
    "decisions": "architecture-decisions",
    "roadmap": "architecture-roadmap",
    "future": "architecture-future",
    # v3 judgment-driven per-module note
    "module": "architecture-module",
    # v3 product-eye types
    "personas": "architecture-personas",
    "jobs": "architecture-jobs",
    "flows": "architecture-flows",
    "ai-flow": "architecture-ai-flow",
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
    "api-surface": ("summary", "interface-overview", "env-overview"),  # DEPRECATED in v4
    "features": ("summary", "capability-scope", "strengths", "weaknesses", "improvements"),  # DEPRECATED
    "decisions": ("summary", "stack-rationale", "detected-adrs", "pattern-decisions",
                  "commit-message-decisions", "promote-to-adr", "known-limitations"),
    "roadmap": ("summary", "near-term", "trajectory", "todo-clusters", "signals-reviewed"),  # DEPRECATED
    "future": ("summary", "known-limitations", "improvements"),  # DEPRECATED
    # v3 module-type — judgment-driven, no file recital.
    "module": ("scope", "strengths", "weaknesses", "improvements", "dependencies"),
    # v4 overview — 8 top-down report sections.
    "overview": (
        "purpose",
        "system-diagram",
        "stack-summary",
        "capabilities",
        "flows",
        "module-map",
        "cross-cutting-improvements",
        "drill-down",
    ),
    # v3 product-eye new types
    "personas": ("summary", "personas-list"),
    "jobs": ("summary", "jobs-list"),  # DEPRECATED
    "flows": ("summary", "flows-list"),  # DEPRECATED
    "ai-flow": (
        "ai-purpose",
        "graph-topology",
        "state-schema",
        "prompts",
        "llm-config",
        "evaluation",
        "strengths",
        "weaknesses",
        "improvements",
        "dependencies",
    ),
}

# v4 — these sections are still callable for backward compat but no longer
# emitted by the default `--frame=report` pipeline. The v3 vault migration
# deletes their vault files; the schema entries stay so old vaults still load.
DEPRECATED_SECTIONS = frozenset({
    "api-surface", "features", "roadmap", "future", "jobs", "flows",
})

# Canonical English H2 heading per @generated block name. Translated at render
# time via lang.heading() for zh-TW vaults. Keys are the SAME slug-style names
# used in _BLOCK_NAMES so the loop in compose_note() can look them up directly.
_BLOCK_HEADINGS = {
    "summary": "## Summary",
    # api-surface (v3 — high-level, not full table)
    "interface-overview": "## Interface overview",
    "env-overview": "## Environment variables overview",
    # features (v3)
    "capability-scope": "## Capability scope",
    # decisions (unchanged)
    "stack-rationale": "## Stack rationale",
    "detected-adrs": "## Detected ADRs",
    "pattern-decisions": "## Pattern decisions",
    "commit-message-decisions": "## Commit-message decisions",
    "promote-to-adr": "## Promote to ADR",
    # roadmap (unchanged)
    "near-term": "## Near term",
    "trajectory": "## Trajectory",
    "todo-clusters": "## TODO clusters",
    "signals-reviewed": "## Signals reviewed",
    # future (v3 — drops gap-analysis & aspirational-ideas; uses improvements)
    "known-limitations": "## Known limitations",
    # v3 module judgment
    "scope": "## Module responsibility",
    "strengths": "## Design strengths",
    "weaknesses": "## Design weaknesses",
    "improvements": "## Improvement opportunities",
    "dependencies": "## Dependencies and consumers",
    # product-eye
    "personas-list": "## Personas",
    "jobs-list": "## Jobs to be done",
    "flows-list": "## Flows",
    # v4 overview report sections
    "purpose": "## Purpose & audience",
    "system-diagram": "## System diagram",
    "stack-summary": "## Stack",
    "capabilities": "## Capabilities",
    "flows": "## Flows",
    "module-map": "## Module map",
    "cross-cutting-improvements": "## Cross-cutting improvements",
    "drill-down": "## Drill-down entries",
    # v4.1 ai-flow report sections
    "ai-purpose": "## Purpose",
    "graph-topology": "## Graph topology",
    "state-schema": "## State schema",
    "prompts": "## Prompts",
    "llm-config": "## LLM config",
    "evaluation": "## Evaluation & observability",
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


def _repo_yaml_lines(repo_label: str) -> list[str]:
    """Normalize `repo_label` into safe YAML frontmatter line(s).

    Obsidian's strict YAML parser flags `repo: local: /abs/path` as an invalid
    property because the unquoted value has an embedded colon. Split into two
    distinct fields and always quote the value to be safe.

    - "local: <path>" or "/abs/path" -> `local-path: "<path>"`
    - everything else (URL, repo nickname) -> `repo: "<value>"`
    """
    stripped = repo_label.strip()
    if stripped.startswith("local:"):
        local_path = stripped[len("local:"):].strip()
        return [f'local-path: "{local_path}"']
    if stripped.startswith("/"):
        return [f'local-path: "{stripped}"']
    return [f'repo: "{stripped}"']


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
    if section in DEPRECATED_SECTIONS:
        _logger.warning(
            "compose_note(section=%r) — this section type is DEPRECATED in v4. "
            "It is still callable for backward compat but no longer emitted by "
            "the default --frame=report pipeline.",
            section,
        )
    tag_suffix = section.replace("-", "-")  # keep stable; e.g. "api-surface"
    fm_lines = [
        "---",
        f"type: {type_value}",
        f"date: {today}",
        f'project: "[[{project}]]"',
        *_repo_yaml_lines(repo_label),
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
        # Emit the section's H2 heading BEFORE the sentinel so the note has real
        # navigable structure. Wikilinks can target `[[file#<heading>]]` and the
        # Obsidian outline shows each section. Heading is bilingual-aware via
        # lang.heading(); falls back to the slug if no mapping exists.
        canonical_h2 = _BLOCK_HEADINGS.get(name, f"## {name}")
        body_parts.append(heading(canonical_h2, output_lang))
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
            "module": "本檔是單一模組的判斷式分析(scope / strengths / weaknesses / improvements / dependencies),不重述檔案列表。要做架構決策或 onboarding 從這裡讀。",
            "personas": "本檔列出推測的使用者/開發者角色,基於 surface area 與功能。多為推論。",
            "jobs": "本檔列出 codebase 為使用者完成的工作 (jobs to be done)。",
            "flows": "本檔列出橫跨模組的關鍵使用者流程或資料流。",
            "ai-flow": "本檔是單一 AI 流程的深判斷 — 包含 graph 結構、state schema、prompts 全文、LLM 設定、評估與設計優缺點。",
        }[section]
    return {
        "api-surface": "This is the API surface reference. Look up commands or endpoints here.",
        "features": "Capabilities exposed by this codebase. See [[Architecture/api-surface]] for the structured tables and [[Architecture/modules]] for per-module depth.",
        "decisions": "Index of key technical decisions. Promote individual entries to full ADRs via /obsidian-adr into Decisions/.",
        "roadmap": "Synthesized from CHANGELOG, README, and TODO clusters. Inference is marked.",
        "future": "Gap analysis and north-star ideas. Mostly inferred, not committed.",
        "module": "Judgment-driven per-module note (scope / strengths / weaknesses / improvements / dependencies). No file recital. Read this before architecture decisions or onboarding.",
        "personas": "Inferred user/developer personas from surface area and features. Mostly speculation.",
        "jobs": "Jobs to be done that this codebase fulfills for users.",
        "flows": "Cross-module user flows or data flows of note.",
        "ai-flow": "Deep judgment for a single AI flow — graph topology, state schema, full prompts, LLM config, evaluation, and design pros/cons.",
    }[section]


def module_for_path(rel_path: str, manifest_modules: list[dict]) -> str | None:
    """Return the slug of the module containing `rel_path`, or None."""
    src = rel_path.split(":")[0]
    for m in manifest_modules:
        for prefix in m.get("paths", []):
            if src == prefix or src.startswith(prefix.rstrip("/") + "/"):
                return m["slug"]
    return None


def render_signals_reviewed(sources: list[str], todo_counts: dict[str, int], lang: str) -> str:
    """Emit the deterministic 'Signals reviewed' tail block."""
    todo_word = "TODOs" if lang == "en" else "個 TODO"
    parts = []
    for src in sources:
        parts.append(f"- `{src}`")
    for slug, n in sorted(todo_counts.items()):
        parts.append(f"- {slug}: {n} {todo_word}" if lang == "en" else f"- {slug}: {n} {todo_word}")
    return "\n".join(parts)


def gap_analysis(*, readme_features: str, api_surface: dict) -> list[str]:
    """Return bullets for features mentioned in README that the scanner could not locate.

    Heuristic: tokenize README feature bullets; check whether ANY surface entry's
    name/path/handler/symbol contains a normalized token. Bullets with no match
    become gap candidates.
    """
    if not readme_features:
        return []
    surface_strings = []
    for c in api_surface.get("cli_commands", []):
        surface_strings.append(c.get("name", "").lower())
        surface_strings.append(c.get("description", "").lower())
    for r in api_surface.get("http_routes", []):
        surface_strings.append(r.get("path", "").lower())
        surface_strings.append(r.get("handler", "").lower())
    for e in api_surface.get("exports", []):
        surface_strings.append(e.get("symbol", "").lower())
    haystack = " ".join(surface_strings)

    gaps: list[str] = []
    for line in readme_features.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        bullet = line.lstrip("- ").strip()
        tokens = [t for t in bullet.lower().split() if len(t) > 3]
        if not any(t in haystack for t in tokens):
            gaps.append(bullet)
    return gaps


_FUNCTION_BLOCK_NAMES = ("what-it-does", "inputs-and-outputs", "behavior-notes", "callers")


def compose_function_note(
    *,
    project: str,
    repo_label: str,
    module_slug: str,
    name: str,
    signature: str,
    source_file: str,
    line_range: str,
    commit: str,
    output_lang: str,
    generated_blocks: dict[str, str],
) -> str:
    today = date.today().isoformat()
    fm = [
        "---",
        "type: architecture-function",
        f"date: {today}",
        f'project: "[[{project}]]"',
        *_repo_yaml_lines(repo_label),
        f"module-slug: {module_slug}",
        f'display-name: "{name}"',
        f'signature: "{signature}"',
        f"source-file: {source_file}",
        f"line-range: {line_range}",
        f"last-scanned: {today}",
        f"commit: {commit}",
        f"lang: {output_lang}",
        "tags: [architecture, function]",
        "ai-first: true",
        "status: current",
        "---",
    ]
    body = [
        "",
        heading("## For future Claude", output_lang),
        ("函式 `" + name + "` 的單頁說明,與 [[modules/" + module_slug + "]] 連動。") if output_lang == "zh-TW"
        else ("Single-function reference for `" + name + "`. See [[modules/" + module_slug + "]] for context."),
        "",
        heading("## Signature", output_lang),
        "```",
        signature,
        "```",
        "",
    ]
    for blk in _FUNCTION_BLOCK_NAMES:
        text = generated_blocks.get(blk, "").strip()
        if not text:
            continue
        # Block name -> canonical heading. Hard-coded to keep heading names exact.
        h_map = {
            "what-it-does": "## What it does",
            "inputs-and-outputs": "## Inputs and outputs",
            "behavior-notes": "## Behavior notes",
            "callers": "## Callers",
        }
        body.append(heading(h_map[blk], output_lang))
        body.append(f"<!-- @generated:start {blk} -->")
        body.append(text)
        body.append(f"<!-- @generated:end {blk} -->")
        body.append("")
    body.append(heading("## Related", output_lang))
    body.append(f"- [[modules/{module_slug}]]")
    body.append(f"- [[Architecture/api-surface]]")
    return "\n".join(fm + body) + "\n"


def _yaml_block(name: str, mapping: dict, indent: int = 2) -> str:
    """Render a simple flat YAML block. Lists are inline JSON-ish."""
    if not mapping:
        return ""
    out = [f"{name}:"]
    pad = " " * indent
    for k, v in mapping.items():
        if isinstance(v, list):
            out.append(f"{pad}{k}: [{', '.join(str(x) for x in v)}]")
        else:
            out.append(f"{pad}{k}: {v}")
    return "\n".join(out)


def compose_overview(
    *,
    project: str,
    repo_label: str,
    commit: str,
    stack: dict,
    output_lang: str,
    modules: list[dict],
    entry_points: list[dict],
    generated_blocks: dict[str, str],
) -> str:
    """Compose the v4 top-down report overview.md.

    Body sections (in order):
      1. Purpose & audience (LLM block: `purpose`)
      2. System diagram (LLM block: `system-diagram`)
      3. Stack (deterministic mirror of frontmatter `stack`)
      4. Capabilities (LLM block: `capabilities`)
      5. Flows (LLM block: `flows`)
      6. Module map (deterministic from `modules` arg)
      7. Cross-cutting improvements (LLM block: `cross-cutting-improvements`)
      8. Drill-down entries (deterministic wikilinks)
    """
    today = date.today().isoformat()
    fm = [
        "---",
        "type: architecture-overview",
        "report-style: true",
        f"date: {today}",
        f'project: "[[{project}]]"',
        *_repo_yaml_lines(repo_label),
        f"last-scanned: {today}",
        f"commit: {commit}",
        f"lang: {output_lang}",
        "tags: [architecture, codebase-doc, report]",
        "ai-first: true",
        "status: current",
    ]
    if stack:
        fm.append(_yaml_block("stack", stack))
    fm.append("---")

    body: list[str] = ["", heading("## For future Claude", output_lang)]
    if output_lang == "zh-TW":
        body.append(
            "本檔一次說完整個 project 的設計。打開這個檔就懂全貌,detail 在 "
            "[[modules/...]] / [[decisions]] / [[personas]]。"
        )
    else:
        body.append(
            "This single file tells the whole project story top-down. Drill into "
            "[[modules/...]] / [[decisions]] / [[personas]] when you need more detail."
        )
    body.append("")

    # 1. Purpose & audience (LLM block)
    body.append(heading("## Purpose & audience", output_lang))
    purpose = generated_blocks.get("purpose", "").strip()
    if purpose:
        body.append("<!-- @generated:start purpose -->")
        body.append(purpose)
        body.append("<!-- @generated:end purpose -->")
    body.append("")

    # 2. System diagram (LLM block, expects Mermaid inside)
    body.append(heading("## System diagram", output_lang))
    diagram = generated_blocks.get("system-diagram", "").strip()
    if diagram:
        body.append("<!-- @generated:start system-diagram -->")
        body.append(diagram)
        body.append("<!-- @generated:end system-diagram -->")
    body.append("")

    # 3. Stack (deterministic mirror of frontmatter)
    body.append(heading("## Stack", output_lang))
    if stack:
        for k, v in stack.items():
            if k == "modules":
                continue  # internal nesting, don't expand here
            if isinstance(v, list):
                body.append(f"- **{k}:** {', '.join(str(x) for x in v)}")
            else:
                body.append(f"- **{k}:** {v}")
        if output_lang == "zh-TW":
            body.append("- (完整理由見 [[decisions#技術棧理由]])")
        else:
            body.append("- (Full rationale in [[decisions#Stack rationale]])")
    else:
        body.append(
            "- (No stack detected. Add `pyproject.toml` / `package.json` at repo root.)"
            if output_lang == "en"
            else "- (Scanner 未偵測到 stack。請在 repo root 加 `pyproject.toml` / `package.json`。)"
        )
    body.append("")

    # 4. Capabilities (LLM block)
    body.append(heading("## Capabilities", output_lang))
    caps = generated_blocks.get("capabilities", "").strip()
    if caps:
        body.append("<!-- @generated:start capabilities -->")
        body.append(caps)
        body.append("<!-- @generated:end capabilities -->")
    body.append("")

    # 5. Flows (LLM block)
    body.append(heading("## Flows", output_lang))
    flows = generated_blocks.get("flows", "").strip()
    if flows:
        body.append("<!-- @generated:start flows -->")
        body.append(flows)
        body.append("<!-- @generated:end flows -->")
    body.append("")

    # 6. Module map (deterministic)
    body.append(heading("## Module map", output_lang))
    for m in modules:
        slug = m["slug"]
        display = m.get("display_name", slug)
        body.append(f"- **{display}** — [[modules/{slug}]]")
    body.append("")

    # 7. Cross-cutting improvements (LLM block, contains Imp 1/2/3 strict format)
    body.append(heading("## Cross-cutting improvements", output_lang))
    imps = generated_blocks.get("cross-cutting-improvements", "").strip()
    if imps:
        body.append("<!-- @generated:start cross-cutting-improvements -->")
        body.append(imps)
        body.append("<!-- @generated:end cross-cutting-improvements -->")
    body.append("")

    # 8. Drill-down entries (deterministic)
    body.append(heading("## Drill-down entries", output_lang))
    if output_lang == "zh-TW":
        body.append("- **模組設計判斷:** " + " | ".join(
            f"[[modules/{m['slug']}]]" for m in modules
        ) if modules else "- **模組設計判斷:** (尚未偵測到模組)")
        body.append("- **完整技術決定 + ADR 候選 + 已知限制:** [[decisions]]")
        body.append("- **使用者型態 reference:** [[personas]]")
        body.append("- **Curated Roadmap + Tasks backlog:** [[Roadmap]] (由 `/obsidian-roadmap` 產出)")
    else:
        body.append("- **Per-module design judgment:** " + " | ".join(
            f"[[modules/{m['slug']}]]" for m in modules
        ) if modules else "- **Per-module design judgment:** (no modules detected)")
        body.append("- **Full technical decisions + ADR candidates + Known limitations:** [[decisions]]")
        body.append("- **Persona reference:** [[personas]]")
        body.append("- **Curated Roadmap + Tasks backlog:** [[Roadmap]] (from `/obsidian-roadmap`)")
    body.append("")

    body.append(heading("## Related", output_lang))
    body.append(f"- [[{project}]]")
    return "\n".join(fm + body) + "\n"


def build_overview_prompt(
    *,
    project: str,
    modules_summary: str,
    agents_md_excerpt: str,
    readme_excerpt: str,
    personas_summary: str,
    per_module_improvements_summary: str,
    output_lang: str,
) -> str:
    """v4 — top-down report overview synthesis prompt.

    The LLM produces 5 blocks; `compose_overview` then assembles with
    deterministic Stack / Module map / Drill-down sections.
    """
    if output_lang == "zh-TW":
        lang_directive = (
            "請以繁體中文 (zh-TW) 撰寫所有 prose。Code identifier (檔名、function、"
            "endpoint path、env var、wikilink 內檔名段) 保持英文。"
        )
    else:
        lang_directive = (
            "Write all prose in English. Code identifiers stay English."
        )

    return "\n".join([
        f"You are writing the v4 top-down architecture *report* for project `{project}`.",
        f"Output language: {output_lang}.",
        lang_directive,
        "",
        "## Critical rules",
        "1. This is a REPORT, not an MOC. The reader opens overview.md and gets the "
        "   whole story; they should NOT need to drill into other files just to "
        "   understand what this project is and what's important about it.",
        "2. The Stack / Module map / Drill-down sections are rendered deterministically "
        "   by the caller — DO NOT produce them. Focus on the 5 LLM blocks below.",
        "3. Cross-cutting improvements MUST be cross-module. Single-module problems "
        "   stay in their module note. Each cross-cutting Imp should cite ≥ 2 modules "
        "   in its Evidence.",
        "",
        "## Output: produce 5 @generated blocks (JSON keys)",
        "",
        "### `purpose`",
        "1 short paragraph + a 3-5 bullet 'For whom' list of primary personas.",
        "  Example shape (zh-TW):",
        "  ```",
        "  - **是什麼:** 一句話定義",
        "  - **服務對象 (主要 personas):**",
        "    - <persona 1> — <one-line role>",
        "    - <persona 2> — <one-line role>",
        "  - **核心承諾:** 1-2 句",
        "  ```",
        "",
        "### `system-diagram`",
        "ONE Mermaid `graph TD` block showing the project at top-down level:",
        "external systems → frontend/backend → internal modules → data layer.",
        "Format:",
        "  ```mermaid",
        "  graph TD",
        "      External --> ...",
        "  ```",
        "Keep ≤ 12 nodes. This is the bird's-eye view; specific flows live in §Flows.",
        "",
        "### `capabilities`",
        "What this codebase DOES, grouped by capability area as H3 sub-sections, "
        "each with 1-3 short bullets. Format:",
        "  ```",
        "  ### Authentication",
        "  - <capability>, links to [[modules/<slug>]]",
        "  ",
        "  ### Webhook ingest",
        "  - <capability>",
        "  ```",
        "Aim for 5-8 capability areas. NO file paths in body prose — wikilinks only.",
        "",
        "### `flows`",
        "3-5 key user-level flows. Each flow is an H3 + Mermaid sequence + 2-4 "
        "friction bullets. Format:",
        "  ```",
        "  ### Flow 1: <name in zh-TW or en>",
        "  ```mermaid",
        "  sequenceDiagram",
        "      participant U as User",
        "      U->>S: ...",
        "  ```",
        "  **摩擦 / Friction:**",
        "  - <concrete pain> → 詳見 [[modules/<slug>#改進機會]]",
        "  - ...",
        "  ```",
        "Pick the most user-visible / business-critical flows. Skip internal-only data flows.",
        "",
        "### `cross-cutting-improvements`",
        "Top 3-5 improvement opportunities that span multiple modules. Each MUST:",
        "  - Be a cross-cutting concern (e.g. 'extract worker convention' impacts "
        "    backend + modules; 'TS migration' impacts frontend × N pages).",
        "  - Cite ≥ 2 modules in Evidence (wikilinks to module Imps).",
        "  - Follow the strict 5-field format:",
        "    ```",
        "    ### Imp <n>: <verb-first title ≤ 30 chars>",
        "    - **為什麼 / Why:** <≤ 1 sentence>",
        "    - **證據 / Evidence:** [[modules/<slug>#改進機會]] Imp N | [[modules/<other>...]] Imp M",
        "    - **Effort:** S | M | L | XL",
        "    - **未做的風險 / Risk if not done:** <≤ 1 sentence>",
        "    - **Confidence:** stated | high | medium | speculation",
        "    ```",
        "  - If you cannot identify cross-module evidence, DO NOT invent the Imp.",
        "",
        "Return strict JSON: {\"purpose\": \"...\", \"system-diagram\": \"...\", "
        "\"capabilities\": \"...\", \"flows\": \"...\", \"cross-cutting-improvements\": \"...\"}.",
        "",
        "## Project context",
        f"### Modules detected: {modules_summary}",
        "",
        "### Personas summary",
        personas_summary[:2000],
        "",
        "### Per-module improvement opportunities (cite these in cross-cutting evidence)",
        per_module_improvements_summary[:4000],
        "",
        "### README excerpt",
        readme_excerpt[:4000],
        "",
        "### AGENTS.md excerpt",
        agents_md_excerpt[:4000],
    ])


SUPPORTED_FRAMES = ("report", "judgment", "description")
DEFAULT_FRAME = "report"


def resolve_frame(cli_flag: str | None) -> str:
    """Return the effective architect frame.

    Precedence: CLI flag > default ('report'). Invalid or empty falls back.
    """
    if cli_flag and cli_flag in SUPPORTED_FRAMES:
        return cli_flag
    return DEFAULT_FRAME


def build_ai_flow_prompt(
    *,
    flow_slug: str,
    flow_name: str,
    framework: str,
    flow_kind: str,
    prompts_inventory: list[dict],
    state_module: str | None,
    graph_files: list[str],
    repomix_packed: str,
    output_lang: str,
) -> str:
    """v4.1 — AI flow synthesis prompt.

    Demands the LLM produce 10 @generated block bodies. Prompts block is special:
    must wrap each prompt body in a collapsible Obsidian callout AND keep
    sentinel structure. Dynamic prompts get a description, NOT a synthesized body.
    """
    if output_lang == "zh-TW":
        lang_directive = (
            "請以繁體中文 (zh-TW) 撰寫所有散文與 heading。"
            "Code identifier (檔名、function/class、state key 名、env var)、"
            "prompt 全文、Mermaid 圖內 node ID 保持英文/原文。"
        )
    else:
        lang_directive = (
            "Write all prose in English. Code identifiers, prompt text, and "
            "Mermaid node IDs stay verbatim."
        )

    # Inventory summary for the prompt (the agent fills in full bodies in block 4).
    prompts_summary_lines = []
    for p in prompts_inventory:
        marker = "(DYNAMIC — describe assembly, do NOT synthesize body)" if p.get("is_dynamic") else ""
        prompts_summary_lines.append(
            f"  - name={p['name']}  source={p['source']}  "
            f"is_dynamic={p.get('is_dynamic', False)} {marker}"
        )
        if not p.get("is_dynamic"):
            preview = p.get("body", "")[:200]
            prompts_summary_lines.append(f"    body preview: {preview!r}")
    prompts_summary = "\n".join(prompts_summary_lines) if prompts_summary_lines else (
        "  (no static prompts extracted)"
    )

    return "\n".join([
        f"You are documenting the AI flow `{flow_slug}` ({flow_name}).",
        f"Framework: {framework}.  Flow kind: {flow_kind}.",
        f"Output language: {output_lang}.",
        lang_directive,
        "",
        "## Critical rules",
        "1. DO NOT invent prompt body text. For each static prompt extracted (see "
        "   inventory below), use its body VERBATIM inside the rendered block. "
        "   For DYNAMIC prompts, write a description of how it is assembled "
        "   (which source files contribute), and DO NOT synthesize a body.",
        "2. Every improvement must cite Evidence — wikilinks to [[modules/<slug>]]"
        " or `path:line`. Drop any Imp you cannot ground in Evidence.",
        "3. Strengths and weaknesses follow the v3.1 tight bullet shape: "
        "**Title (≤ 30 chars).** 1 line clarification (≤ 80 chars).",
        "",
        "## Output: produce 10 @generated blocks (JSON keys)",
        "",
        "### `ai-purpose`",
        "1 paragraph: when this AI runs, for whom, what it solves, what it outputs.",
        "",
        "### `graph-topology`",
        "ONE Mermaid `graph TD` showing nodes + edges + conditional routing. "
        "Each node label includes its source `path:line`.",
        "",
        "### `state-schema`",
        "If a State TypedDict / pydantic model exists (see "
        f"{state_module or '(none found)'}), copy its Python form into a "
        "```python``` block.  If dynamic / dict-only, describe the keys you "
        "see referenced.",
        "",
        "### `prompts`",
        "For EACH prompt in the inventory below, render ONE H3 + 4 metadata bullets +",
        "ONE collapsible callout wrapping the body, inside a per-prompt @generated sentinel.",
        "Format STRICTLY:",
        "  ```",
        "  ### <prompt name>",
        "  - **用途 / Purpose:** <1 句>",
        "  - **Source:** `<path:line-range>`",
        "  - **Model:** <model_hint or unknown>",
        "  - **Type:** static template  OR  dynamic — see assembly notes",
        "",
        "  <!-- @generated:start prompt-<slug> -->",
        "  > [!quote]- 完整 prompt",
        "  > ````",
        "  > <full body verbatim from inventory, OR dynamic description>",
        "  > ````",
        "  <!-- @generated:end prompt-<slug> -->",
        "  ```",
        "Where `prompt-<slug>` uses ascii-lowercase-hyphen of the prompt name.",
        "Do NOT modify the prompt body — copy from inventory below verbatim.",
        "",
        "### `llm-config`",
        "Markdown table: | Role | Model | Temperature | Fallback | Latency budget |",
        "Pull values from the inventory's `model_hint` + any visible `model=...` / "
        "`temperature=...` in graph files.  Mark unknowns as `?`.",
        "",
        "### `evaluation`",
        "Does owner have eval framework? metrics? tracing (LangSmith/Helicone/Phoenix)? "
        "If absent → `> [!warning] 無 eval framework — 評估完全靠人工 / 客訴.` (zh-TW)",
        "",
        "### `strengths`",
        "3-5 tight bullets each with Evidence.",
        "",
        "### `weaknesses`",
        "3-5 tight bullets each with concrete impact. Include AI-specific failure "
        "modes (hallucination / cost / latency / rate-limit / prompt-injection).",
        "",
        "### `improvements`",
        "2-4 Imps. Each MUST contain:",
        "  - **為什麼 / Why:** <≤ 1 sentence>",
        "  - **證據 / Evidence:** wikilink or `path:line`",
        "  - **Effort:** S | M | L | XL",
        "  - **未做的風險 / Risk if not done:** <≤ 1 sentence>",
        "  - **Confidence:** stated | high | medium | speculation",
        "",
        "### `dependencies`",
        "Wikilinks only:",
        "  - Host module:  `[[modules/<host>]]`",
        "  - External APIs:  Gemini / OpenAI / Anthropic / ...",
        "  - Framework:  LangGraph / LangChain (link to decision if exists)",
        "  - Observability:  LangSmith / Phoenix (if stated)",
        "",
        "Return strict JSON: {\"ai-purpose\": \"...\", \"graph-topology\": \"...\", "
        "\"state-schema\": \"...\", \"prompts\": \"...\", \"llm-config\": \"...\", "
        "\"evaluation\": \"...\", \"strengths\": \"...\", \"weaknesses\": \"...\", "
        "\"improvements\": \"...\", \"dependencies\": \"...\"}.",
        "",
        "## Prompts inventory (use these bodies verbatim)",
        prompts_summary,
        "",
        "## Graph files",
        ", ".join(graph_files) if graph_files else "(none detected)",
        "",
        "## Repomix-packed module context",
        repomix_packed[:50000],
    ])


def render_prompts_block(
    inventory: list[dict],
    annotations: dict[str, dict],
    lang: str = "en",
) -> str:
    """Render the `## Prompts` block body for an ai-flow note.

    Each prompt becomes:
      - H3 with the prompt name
      - 4 metadata bullets (Purpose, Source, Model, Type)
      - Per-prompt @generated sentinel wrapping a collapsible callout (static)
        OR an inline description (dynamic)

    Args:
        inventory: list of ExtractedPrompt-asdict (from scan-report.json's ai_flows[N].prompts).
        annotations: dict[prompt-name → {purpose: str, type_note: str}] — the agent's per-prompt copy.
        lang: 'en' | 'zh-TW'.
    """
    if not inventory:
        return (
            "(未偵測到 prompts;若有動態組合 prompt,請手動補入 @user 區塊)"
            if lang == "zh-TW"
            else "(no static prompts extracted; add dynamic prompts manually in @user blocks)"
        )

    labels = {
        "zh-TW": {"purpose": "用途", "type_static": "static template", "type_dynamic": "dynamic",
                  "callout": "> [!quote]- 完整 prompt"},
        "en": {"purpose": "Purpose", "type_static": "static template", "type_dynamic": "dynamic",
               "callout": "> [!quote]- Full prompt"},
    }[lang]

    out: list[str] = []
    for entry in inventory:
        name = entry["name"]
        slug = _slugify_prompt(name)
        purpose = annotations.get(name, {}).get("purpose", "(LLM 未補上 / not annotated)")
        type_value = labels["type_dynamic"] if entry.get("is_dynamic") else labels["type_static"]
        type_note = annotations.get(name, {}).get("type_note", "")
        if type_note:
            type_value = f"{type_value} — {type_note}"

        out.append(f"### {name}")
        out.append(f"- **{labels['purpose']}:** {purpose}")
        out.append(f"- **Source:** `{entry['source']}`")
        model = entry.get("model_hint") or "?"
        out.append(f"- **Model:** {model}")
        out.append(f"- **Type:** {type_value}")
        out.append("")
        out.append(f"<!-- @generated:start prompt-{slug} -->")
        if entry.get("is_dynamic"):
            # Dynamic prompts: inline description, no collapsible callout.
            out.append(entry["body"])
        else:
            out.append(labels["callout"])
            out.append("> ````")
            for line in entry["body"].splitlines():
                out.append(f"> {line}")
            out.append("> ````")
        out.append(f"<!-- @generated:end prompt-{slug} -->")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


_SLUG_NORM_RE = re.compile(r"[^a-z0-9-]+")


def _slugify_prompt(name: str) -> str:
    """Prompt name → ascii-lowercase-hyphen slug suitable for sentinel name."""
    s = name.lower()
    s = _SLUG_NORM_RE.sub("-", s).strip("-")
    return s or "unknown"


def build_module_prompt(
    *,
    module_slug: str,
    repomix_packed: str,
    agents_md_excerpt: str,
    output_lang: str,
) -> str:
    """v3 — judgment-driven module synthesis prompt.

    NO file listing. The agent demands strengths / weaknesses / improvements,
    each grounded in Evidence (commit, decision wikilink, code path:line).
    """
    if output_lang == "zh-TW":
        lang_directive = (
            "請以繁體中文 (zh-TW) 撰寫 scope/strengths/weaknesses/improvements 段散文。"
            "Code identifier (檔名、function/class、env var、wikilink 內檔名段) "
            "保持英文。Evidence 中可包含 `path:line` inline 引用。"
        )
    else:
        lang_directive = (
            "Write scope/strengths/weaknesses/improvements prose in English. "
            "Code identifiers stay English. Evidence may include `path:line` inline citations."
        )

    return "\n".join([
        f"You are writing the architecture *judgment* document for module `{module_slug}`.",
        f"Output language: {output_lang}.",
        lang_directive,
        "",
        "## Critical rules",
        "1. DO NOT list files. The codebase is the source of truth — vault notes "
        "   capture judgment that the codebase does NOT record (design tradeoffs, risks, "
        "   improvement opportunities).",
        "2. DO NOT generate 'how it works' style transcription. If a reader needs that, "
        "   they read the code.",
        "3. EVERY improvement must cite Evidence. If you cannot cite Evidence for an idea, "
        "   DO NOT include that improvement — drop it. We refuse speculative roadmap items.",
        "",
        "## Bullet density rules (HARD — judge yourself before you ship)",
        "Every bullet in strengths/weaknesses follows this exact shape:",
        "  - **Title (≤ 30 chars, noun phrase or 動詞短句).** 1 line clarification (≤ 80 chars).",
        "    - Evidence: `path:line` | [[wikilink]] | commit `<sha>`",
        "",
        "✅ GOOD:",
        "  - **host-net + announce 避開 127.0.0.1 重導.** Client 透過 announce 拿到真實私網 IP。",
        "    - Evidence: `services/postgres-redis-lab/docker-compose.yaml`, `bootstrap-redis-cluster.sh`",
        "",
        "❌ BAD (this exact pattern broke the v3.0 output — do NOT generate this style):",
        "  - **Postgres + Redis 共用 `network_mode: host`,讓 announce 設計能套用真實私網 IP** — `services/postgres-redis-lab/docker-compose.yaml` 全部節點 `network_mode: host`,並透過 `REDIS_CLUSTER_ANNOUNCE_HOST` 將遠端可達位址廣告給 client (`services/postgres-redis-lab/scripts/bootstrap-redis-cluster.sh`)。這直接解決了「從 laptop 連線到 server 的 Redis Cluster 時 client 收到 `127.0.0.1` 重導」的經典陷阱。",
        "  (Reasons: 100+ char title; evidence buried inline; trailing 'this directly solves X' filler.)",
        "",
        "## No-filler rules (HARD)",
        "Forbidden bridging phrases — cut them at write time:",
        "  ❌ '這直接解決了 X 的經典陷阱' / 'this directly solves the classic X pitfall'",
        "  ❌ '比把密碼塞進 image 的習慣安全得多' / 'much safer than X'",
        "  ❌ '這非常重要' / 'this is very important'",
        "  ❌ '值得一提的是' / 'it is worth noting'",
        "  ❌ '進一步強化了' / 'further reinforces'",
        "  ❌ '不愧是' / 'lives up to its reputation'",
        "Just state the fact. The reader sees the implication.",
        "",
        "## Output: produce 5 @generated blocks (JSON keys)",
        "- `scope` — 1–2 短段 (each ≤ 4 句): what this module owns, its boundary. "
        "  Small Mermaid OK only if a key data-flow is non-obvious from code. Don't draw 'here are 5 routers' diagrams.",
        "- `strengths` — 3–5 bullets following the density rules above.",
        "- `weaknesses` — 3–5 bullets, each names a concrete impact ('peak-load latency spikes because event consumer shares API process') not vague critique ('could be better').",
        "- `improvements` — 2–4 improvement opportunities. Each MUST contain ALL five fields and NOTHING extra:",
        "    ### Imp <n>: <title (≤ 30 chars, verb-first)>",
        "    - **Why:** <≤ 1 sentence, problem statement>",
        "    - **Evidence:** <wikilink or `path:line`>",
        "    - **Effort:** S | M | L | XL",
        "    - **Risk if not done:** <≤ 1 sentence, concrete>",
        "    - **Confidence:** stated | high | medium | speculation",
        "  Omit Imps you cannot fully fill in — quality over quantity. No long Why prose.",
        "- `dependencies` — wikilinks only, each ≤ 1 line. No file paths. No explanations longer than the wikilink.",
        "",
        "Return strict JSON: {\"scope\": \"...\", \"strengths\": \"...\", \"weaknesses\": \"...\", "
        "\"improvements\": \"...\", \"dependencies\": \"...\"}.",
        "",
        "## Module context (repomix packed)",
        repomix_packed[:50000],  # cap to avoid blowing the prompt
        "",
        "## AGENTS.md excerpt",
        agents_md_excerpt[:5000],
    ])


@dataclass
class ImprovementItem:
    title: str
    why: str
    evidence: list[str]
    effort: str               # S | M | L | XL
    risk_if_not_done: str
    confidence: str           # stated | high | medium | speculation


_FIELD_LABELS = {
    "en": {
        "Why": "Why",
        "Evidence": "Evidence",
        "Effort": "Effort",
        "Risk if not done": "Risk if not done",
        "Confidence": "Confidence",
    },
    "zh-TW": {
        "Why": "為什麼",
        "Evidence": "證據",
        "Effort": "Effort",
        "Risk if not done": "未做的風險",
        "Confidence": "Confidence",
    },
}


def render_improvements_block(items: list[ImprovementItem], lang: str = "en") -> str:
    """Render a list of ImprovementItem into the canonical markdown shape.

    Format is strict (see _IMP_RE for the inverse parser):
      ### Imp <n>: <title>
      - **Why:** <prose>
      - **Evidence:** <link1> | <link2>
      - **Effort:** S|M|L|XL
      - **Risk if not done:** <prose>
      - **Confidence:** stated|high|medium|speculation
    """
    labels = _FIELD_LABELS.get(lang, _FIELD_LABELS["en"])
    lines: list[str] = []
    for i, it in enumerate(items, 1):
        lines.append(f"### Imp {i}: {it.title}")
        lines.append(f"- **{labels['Why']}:** {it.why}")
        evidence_str = " | ".join(it.evidence) if it.evidence else "(none)"
        lines.append(f"- **{labels['Evidence']}:** {evidence_str}")
        lines.append(f"- **{labels['Effort']}:** {it.effort}")
        lines.append(f"- **{labels['Risk if not done']}:** {it.risk_if_not_done}")
        lines.append(f"- **{labels['Confidence']}:** {it.confidence}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# Title line.
_IMP_TITLE_RE = re.compile(r"^###\s+Imp\s+\d+:\s+(.+?)\s*$", re.MULTILINE)
# Generic bold-prefix bullet:  - **Label:** Body
_IMP_BULLET_RE = re.compile(r"^-\s+\*\*([^*]+?):\*\*\s*(.+?)\s*$", re.MULTILINE)


def parse_improvements_block(text: str) -> list[ImprovementItem]:
    """Parse a markdown improvements block back into ImprovementItem list.

    Tolerant of zh-TW or en labels. An Imp missing any of the 5 required
    fields is silently dropped (we refuse partial roadmap candidates).
    """
    items: list[ImprovementItem] = []
    # Split text by Imp title boundaries.
    parts = _IMP_TITLE_RE.split(text)
    # _IMP_TITLE_RE.split returns: [before_first, title1, body1, title2, body2, ...]
    if len(parts) < 3:
        return []
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        fields: dict[str, str] = {}
        for m in _IMP_BULLET_RE.finditer(body):
            label_raw = m.group(1).strip()
            value = m.group(2).strip()
            canonical = _canonicalize_field_label(label_raw)
            if canonical:
                fields[canonical] = value
        required = {"Why", "Evidence", "Effort", "Risk if not done", "Confidence"}
        if not required.issubset(fields.keys()):
            continue
        evidence = [e.strip() for e in fields["Evidence"].split("|") if e.strip()]
        items.append(ImprovementItem(
            title=title,
            why=fields["Why"],
            evidence=evidence,
            effort=fields["Effort"],
            risk_if_not_done=fields["Risk if not done"],
            confidence=fields["Confidence"],
        ))
    return items


_LABEL_ALIASES = {
    # Canonical key -> aliases in either language
    "Why": {"why", "為什麼"},
    "Evidence": {"evidence", "證據"},
    "Effort": {"effort"},
    "Risk if not done": {"risk if not done", "未做的風險", "risk"},
    "Confidence": {"confidence"},
}


def _canonicalize_field_label(label_raw: str) -> str | None:
    needle = label_raw.lower()
    for canonical, aliases in _LABEL_ALIASES.items():
        if needle in {a.lower() for a in aliases}:
            return canonical
    return None


_CONFIDENCE_RANK = {"stated": 0, "high": 1, "medium": 2, "speculation": 3}


def enforce_improvements_cap(items: list[ImprovementItem], max_n: int = 4) -> list[ImprovementItem]:
    """Drop excess Imps when LLM returned more than the configured cap.

    Sort by confidence rank (stated > high > medium > speculation) ascending
    so higher-confidence Imps survive, then preserve original ordering within
    same-confidence groups.
    """
    if len(items) <= max_n:
        return items
    indexed = list(enumerate(items))
    indexed.sort(key=lambda pair: (_CONFIDENCE_RANK.get(pair[1].confidence, 99), pair[0]))
    keep = sorted(indexed[:max_n], key=lambda pair: pair[0])
    return [it for _, it in keep]


def enforce_evidence_required(items: list[ImprovementItem], require: bool = True) -> list[ImprovementItem]:
    """Drop Imps with empty evidence when `require=True`.

    Default behaviour for v3. Pass `require=False` (via `--require-evidence`
    flag set to false) to allow Evidence-free Imps during debugging.
    """
    if not require:
        return items
    return [it for it in items if it.evidence]
