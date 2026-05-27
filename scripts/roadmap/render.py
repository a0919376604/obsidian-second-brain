"""Phase 5 — deterministic markdown composers.

These consume LLM-produced Theme/Task dataclasses and assemble:
- Roadmap.md (project-level curated view)
- Tasks/T-NNN-slug.md (one per task, /obsidian-task schema)
- board.md card line (single string appended to ## 待辦)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from scripts.architect.lang import heading


@dataclass
class Task:
    id: str                       # "T-001"
    slug: str                     # "add-engine-adapter-base"
    description: str              # one-line zh-TW
    module_wikilink: str          # "[[modules/backend]]"
    acceptance_criteria: list[str]


@dataclass
class Theme:
    slug: str
    title: str
    why: str
    priority: str                 # "🔴" | "🟡" | "🟢"
    effort: str                   # "S" | "M" | "L" | "XL"
    evidence: list[str]
    tasks: list[Task]
    status: str = "active"        # active | stale


def compose_roadmap(
    *,
    project: str,
    themes: list[Theme],
    stale_themes: list[Theme],
    synthesis_summary: dict,
    output_lang: str,
) -> str:
    today = date.today().isoformat()
    tasks_count = sum(len(t.tasks) for t in themes)
    fm = [
        "---",
        "type: roadmap",
        f"date: {today}",
        f"updated: {today}",
        f'project: "[[{project}]]"',
        f"lang: {output_lang}",
        f"tags: [roadmap, {project}]",
        "ai-first: true",
        "status: active",
        f"last-synthesis: {today}",
        f"themes-count: {len(themes)}",
        f"tasks-count: {tasks_count}",
        "---",
    ]

    body: list[str] = ["", heading("## For future Claude", output_lang)]
    if output_lang == "zh-TW":
        body.append("這是 curated roadmap。策略主題對應原子 task。每個主題的 evidence 區指回 signal 來源。"
                    "Re-run 自動 dedup 並標 stale 主題。")
    else:
        body.append("Curated project roadmap. Themes group atomic tasks; evidence wikilinks "
                    "back to architect signal sources. Re-runs dedup and mark stale themes.")
    body.append("")

    # Synthesis summary
    body.append(heading("## Synthesis summary", output_lang))
    body.append("<!-- @generated:start synthesis-summary -->")
    if output_lang == "zh-TW":
        body.append(f"- 主題: {synthesis_summary['themes']}")
        body.append(f"- Tasks: {synthesis_summary['tasks']}")
        body.append(f"- 引用 research 篇數: {synthesis_summary['research_cited']}")
        body.append(f"- Architect signal 數: {synthesis_summary['architect_signals']}")
    else:
        body.append(f"- Themes: {synthesis_summary['themes']}")
        body.append(f"- Tasks: {synthesis_summary['tasks']}")
        body.append(f"- Research notes cited: {synthesis_summary['research_cited']}")
        body.append(f"- Architect signals used: {synthesis_summary['architect_signals']}")
    body.append("<!-- @generated:end synthesis-summary -->")
    body.append("")

    # Themes
    body.append(heading("## Themes", output_lang))
    body.append("<!-- @generated:start themes -->")
    for t in themes:
        body.extend(_render_theme(t, output_lang))
        body.append("")
    body.append("<!-- @generated:end themes -->")
    body.append("")

    # Stale
    if stale_themes:
        body.append(heading("## Stale themes", output_lang))
        body.append("<!-- @generated:start stale-themes -->")
        for t in stale_themes:
            body.append(f"### {t.title}")
            if output_lang == "zh-TW":
                body.append(f"_status: stale_ — signal 來源消失,留檔不刪。")
            else:
                body.append(f"_status: stale_ — signal source disappeared; kept for history.")
            body.append("")
        body.append("<!-- @generated:end stale-themes -->")
        body.append("")

    body.append(heading("## Related", output_lang))
    body.append(f"- [[{project}]]")
    body.append("- [[Architecture/overview]]")
    body.append("- [[board]]")

    return "\n".join(fm + body) + "\n"


def _render_theme(t: Theme, lang: str) -> list[str]:
    why_label = "為什麼" if lang == "zh-TW" else "Why"
    effort_label = "Effort" if lang == "en" else "Effort"
    evidence_label = "佐證" if lang == "zh-TW" else "Evidence"
    tasks_label = "Tasks"
    out = [f"### {t.priority} {t.title}"]
    out.append(f"**{why_label}:** {t.why}")
    out.append(f"**{effort_label}:** {t.effort}")
    if t.evidence:
        out.append(f"**{evidence_label}:**")
        for e in t.evidence:
            out.append(f"- {e}")
    if t.tasks:
        out.append(f"**{tasks_label}:**")
        for task in t.tasks:
            out.append(f"- [[Tasks/{task.id}-{task.slug}|{task.id} {task.description}]]")
    return out


def compose_task_note(
    *,
    task: Task,
    theme_slug: str,
    theme_title: str,
    project: str,
    output_lang: str,
) -> str:
    today = date.today().isoformat()
    fm = [
        "---",
        "type: task",
        f"date: {today}",
        f'project: "[[{project}]]"',
        f"roadmap-theme: {theme_slug}",
        f'created-by: "obsidian-roadmap"',
        f"lang: {output_lang}",
        "status: backlog",
        "priority: 🟡",
        f"tags: [task, {project}, {theme_slug}]",
        "ai-first: true",
        "---",
    ]
    body = ["", heading("## For future Claude", output_lang)]
    if output_lang == "zh-TW":
        body.append(f"任務 `{task.id}` — {task.description}。屬於 roadmap 主題「{theme_title}」。")
    else:
        body.append(f"Task `{task.id}` — {task.description}. Part of roadmap theme \"{theme_title}\".")
    body.append("")

    body.append(heading("## Acceptance criteria", output_lang))
    if task.acceptance_criteria:
        for c in task.acceptance_criteria:
            body.append(f"- {c}")
    else:
        body.append("_(待定義)_" if output_lang == "zh-TW" else "_(to be defined)_")
    body.append("")

    body.append(heading("## Related", output_lang))
    body.append("- [[Roadmap]]")
    body.append(f"- [[Roadmap#{theme_title}]]")
    if task.module_wikilink:
        body.append(f"- {task.module_wikilink}")
    return "\n".join(fm + body) + "\n"


def format_board_card(task: Task, theme_slug: str, priority: str) -> str:
    """Single line appended to board.md ## 待辦 section."""
    return f"- [ ] [[Tasks/{task.id}-{task.slug}|{task.description}]] {priority} [theme: {theme_slug}]"
