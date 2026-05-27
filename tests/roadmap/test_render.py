from datetime import date

from scripts.roadmap.render import (
    Theme,
    Task,
    compose_roadmap,
    compose_task_note,
    format_board_card,
)


def _sample_themes() -> list[Theme]:
    return [
        Theme(
            slug="ai-engine-pluggability",
            title="AI 引擎可插拔化",
            why="目前只支援 LangGraph (見 [[modules/backend]]);AGENTS.md 提 pluggable engine 但未落實。",
            priority="🔴",
            effort="M",
            evidence=["[[Architecture/future#期望中的想法]] 第 1 點",
                      "[[Projects/p/Research/2026-05-15-engine-comparison]]"],
            tasks=[
                Task(id="T-001", slug="add-engine-adapter-base",
                     description="在 backend/engines/ 加 EngineAdapter base class",
                     module_wikilink="[[modules/backend]]",
                     acceptance_criteria=["`backend/engines/adapter.py` 有 EngineAdapter ABC"]),
                Task(id="T-002", slug="port-langgraph-as-adapter",
                     description="把 LangGraph 實作改寫為 LangGraphAdapter",
                     module_wikilink="[[modules/backend]]",
                     acceptance_criteria=["adapter 通過整合測試"]),
            ],
        ),
    ]


def test_compose_roadmap_emits_frontmatter_and_themes_section_zh():
    note = compose_roadmap(
        project="myproj",
        themes=_sample_themes(),
        stale_themes=[],
        synthesis_summary={"themes": 1, "tasks": 2, "research_cited": 1, "architect_signals": 2},
        output_lang="zh-TW",
    )
    assert note.startswith("---\n")
    assert "type: roadmap" in note
    assert 'project: "[[myproj]]"' in note
    assert "lang: zh-TW" in note
    assert "themes-count: 1" in note
    assert "tasks-count: 2" in note
    assert "## 給未來 Claude" in note
    assert "## 本次合成摘要" in note
    assert "## 主題" in note
    # Theme heading appears as H3
    assert "### 🔴 AI 引擎可插拔化" in note
    # Tasks are wiki-linked
    assert "[[Tasks/T-001-add-engine-adapter-base|T-001 在 backend/engines/ 加 EngineAdapter base class]]" in note
    # Evidence rendered as bullets
    assert "[[Architecture/future#期望中的想法]]" in note


def test_compose_roadmap_en_translates_headings():
    note = compose_roadmap(
        project="myproj",
        themes=_sample_themes(),
        stale_themes=[],
        synthesis_summary={"themes": 1, "tasks": 2, "research_cited": 0, "architect_signals": 1},
        output_lang="en",
    )
    assert "## For future Claude" in note
    assert "## Synthesis summary" in note
    assert "## Themes" in note
    assert "## 給未來 Claude" not in note


def test_compose_roadmap_renders_stale_section():
    note = compose_roadmap(
        project="myproj",
        themes=_sample_themes(),
        stale_themes=[
            Theme(slug="dropped-thing", title="放棄的東西", why="signal disappeared",
                  priority="🟢", effort="S", evidence=[], tasks=[]),
        ],
        synthesis_summary={"themes": 1, "tasks": 2, "research_cited": 0, "architect_signals": 1},
        output_lang="zh-TW",
    )
    assert "## 過時主題" in note
    assert "放棄的東西" in note


def test_compose_task_note_zh():
    t = Task(id="T-001", slug="add-engine-adapter-base",
             description="在 backend/engines/ 加 EngineAdapter base class",
             module_wikilink="[[modules/backend]]",
             acceptance_criteria=["`backend/engines/adapter.py` 有 EngineAdapter ABC",
                                  "既有 LangGraph 可以 instantiate 為 adapter"])
    note = compose_task_note(
        task=t,
        theme_slug="ai-engine-pluggability",
        theme_title="AI 引擎可插拔化",
        project="myproj",
        output_lang="zh-TW",
    )
    assert "type: task" in note
    assert "roadmap-theme: ai-engine-pluggability" in note
    assert 'created-by: "obsidian-roadmap"' in note
    assert "status: backlog" in note
    assert "## 給未來 Claude" in note
    assert "## 接受條件" in note
    assert "EngineAdapter ABC" in note
    assert "[[Roadmap]]" in note
    assert "[[modules/backend]]" in note


def test_format_board_card_carries_theme_label():
    t = Task(id="T-007", slug="add-rate-limit",
             description="加 rate limit middleware",
             module_wikilink="[[modules/backend]]",
             acceptance_criteria=[])
    card = format_board_card(t, theme_slug="observability", priority="🔴")
    assert card.startswith("- [ ]")
    assert "[[Tasks/T-007-add-rate-limit|加 rate limit middleware]]" in card
    assert "🔴" in card
    assert "[theme: observability]" in card
