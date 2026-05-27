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
    "api-surface": ("summary", "interface-overview", "env-overview"),
    "features": ("summary", "capability-scope", "strengths", "weaknesses", "improvements"),
    "decisions": ("summary", "stack-rationale", "detected-adrs", "pattern-decisions",
                  "commit-message-decisions", "promote-to-adr"),
    "roadmap": ("summary", "near-term", "trajectory", "todo-clusters", "signals-reviewed"),
    "future": ("summary", "known-limitations", "improvements"),
    # v3 module-type — judgment-driven, no file recital.
    "module": ("scope", "strengths", "weaknesses", "improvements", "dependencies"),
    # v3 product-eye new types
    "personas": ("summary", "personas-list"),
    "jobs": ("summary", "jobs-list"),
    "flows": ("summary", "flows-list"),
}

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
        f"repo: {repo_label}",
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
    """Compose the MOC-style overview.md."""
    today = date.today().isoformat()
    fm = [
        "---",
        "type: architecture-overview",
        "moc-style: true",
        f"date: {today}",
        f'project: "[[{project}]]"',
        f"repo: {repo_label}",
        f"last-scanned: {today}",
        f"commit: {commit}",
        f"lang: {output_lang}",
        "tags: [architecture, codebase-doc, moc]",
        "ai-first: true",
        "status: current",
    ]
    if stack:
        fm.append(_yaml_block("stack", stack))
    fm.append("---")

    body = [
        "",
        heading("## For future Claude", output_lang),
    ]
    if output_lang == "zh-TW":
        body.append("這個檔是 MOC。不要直接讀這裡的內容,跟著 wikilink 走。每個深入內容在自己的 note,future-Claude 想 grep 一段就 grep 那一段。")
    else:
        body.append("This note is a MOC. Don't read it for content — follow the wikilinks. Each deep-dive lives in its own note so you can grep one without loading the rest.")
    body.append("")

    # Purpose (LLM block).
    if generated_blocks.get("purpose"):
        body.append(heading("## Purpose", output_lang))
        body.append("<!-- @generated:start purpose -->")
        body.append(generated_blocks["purpose"])
        body.append("<!-- @generated:end purpose -->")
        body.append("")

    # Stack (mirrors frontmatter, deterministic).
    if stack:
        body.append(heading("## Stack", output_lang))
        for k, v in stack.items():
            if isinstance(v, list):
                body.append(f"- **{k}:** {', '.join(str(x) for x in v)}")
            else:
                body.append(f"- **{k}:** {v}")
        suffix = "(見 [[Architecture/decisions]] 的理由)" if output_lang == "zh-TW" else "(see [[Architecture/decisions]] for rationale)"
        body.append("")
        body.append(suffix)
        body.append("")

    # Capability MOC (deterministic).
    body.append(heading("## Capability MOC", output_lang))
    body.append("- [[Architecture/features]]")
    body.append("- [[Architecture/roadmap]]")
    body.append("- [[Architecture/decisions]]")
    body.append("- [[Architecture/future]]")
    body.append("")
    body.append(heading("## API surface", output_lang))
    body.append("- [[Architecture/api-surface]]")
    body.append("")

    # Structure MOC (deterministic).
    body.append(heading("## Structure MOC", output_lang))
    for m in modules:
        body.append(f"- [[modules/{m['slug']}]]")
    if entry_points:
        ep_label = "Entry points" if output_lang == "en" else "進入點"
        body.append(f"- **{ep_label}:**")
        for ep in entry_points:
            body.append(f"  - `{ep['label']}` -> `{ep['path']}`")
    body.append("")

    # Layer map (LLM block).
    if generated_blocks.get("layer-map"):
        body.append(heading("## Layer map", output_lang))
        body.append("<!-- @generated:start layer-map -->")
        body.append(generated_blocks["layer-map"])
        body.append("<!-- @generated:end layer-map -->")
        body.append("")

    # External deps (LLM block, deterministic-ish).
    if generated_blocks.get("external-deps"):
        body.append(heading("## External dependencies", output_lang))
        body.append("<!-- @generated:start external-deps -->")
        body.append(generated_blocks["external-deps"])
        body.append("<!-- @generated:end external-deps -->")
        body.append("")

    # Key abstractions (LLM).
    if generated_blocks.get("key-abstractions"):
        body.append(heading("## Key abstractions", output_lang))
        body.append("<!-- @generated:start key-abstractions -->")
        body.append(generated_blocks["key-abstractions"])
        body.append("<!-- @generated:end key-abstractions -->")
        body.append("")

    body.append(heading("## Related", output_lang))
    body.append(f"- [[{project}]]")
    return "\n".join(fm + body) + "\n"


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
        "## Output: produce 5 @generated blocks (JSON keys)",
        "- `scope` — 1–2 paragraphs: what is this module's responsibility, its boundary, "
        "  how it earns its place. May include a small Mermaid diagram if a flow matters.",
        "- `strengths` — 3–5 bullets, each ≤ 2 sentences, each with concrete Evidence "
        "  (commit SHA, ADR wikilink, AGENTS.md section, or `path:line`).",
        "- `weaknesses` — 3–5 bullets, each with concrete impact ('peak-load latency spikes "
        "  because event consumer shares the API process' — not 'could be better').",
        "- `improvements` — 2–4 improvement opportunities. Each MUST contain all five fields:",
        "    - **Why:** what problem it solves",
        "    - **Evidence:** wikilink or `path:line` showing the pain is real",
        "    - **Effort:** one of S | M | L | XL",
        "    - **Risk if not done:** concrete consequence",
        "    - **Confidence:** stated | high | medium | speculation",
        "  Omit Imps you cannot fully fill in — quality over quantity.",
        "- `dependencies` — wikilinks only (e.g. `[[modules/services]]`, `[[Architecture/decisions]]`). "
        "  NO file paths.",
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
