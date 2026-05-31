# `/obsidian-brainstorm` v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-design `/obsidian-brainstorm` to mimic the `superpowers:brainstorming` flow (one-question-at-a-time, multi-choice preferred, lazy code-fetch, propose 2-3 approaches with trade-off matrix, section-by-section design walk) and emit dual output (engineering spec + vault note).

**Architecture:** This skill is **markdown instruction**, not Python. The "implementation" is a rewrite of `commands/obsidian-brainstorm.md` (the LLM-procedure file) plus a new reference file (`references/brainstorm-question-templates.md`) and doc sync across `SKILL.md` / `README.md` / `CHANGELOG.md`. Adapters auto-regenerate via `bash scripts/build.sh`.

**Tech Stack:** Markdown, YAML frontmatter, Bash (build script). No Python helper, no test framework introduced (per CON-001 in spec).

**Spec:** `docs/superpowers/specs/2026-06-01-obsidian-brainstorm-v2-design.md`

**Brainstorm provenance:** `Projects/obsidian-second-brain/Brainstorms/2026-06-01-obsidian-brainstorm-v2.md` (vault path)

---

## Important: TDD adaptation for markdown skills

This repo has **no automated test framework** (per `SKILL.md` line 1, and CON-001 in spec). Standard `pytest`-style TDD does not apply. We adapt the TDD pattern as follows:

- "Write the failing test" → write a verification command (grep / ls / bash check) that we expect to fail before the change.
- "Run it to make sure it fails" → run that verification BEFORE making the change.
- "Implement the minimal change" → write or edit the markdown file.
- "Run the test to verify it passes" → run the same verification AFTER, expecting success.
- "Commit" → atomic commit per task.

Smoke verification (Tier 1 / Tier 2 from spec Section 8) is manual — it requires invoking the skill in a Claude Code session. The final task documents the smoke protocol but does not "run" it programmatically.

---

## File Layout

| File | Action | LOC scale |
|---|---|---|
| `references/brainstorm-question-templates.md` | Create | ~120 |
| `commands/obsidian-brainstorm.md` | Rewrite | +~200 / -~150 |
| `SKILL.md` | Modify (description sync) | +~5 / -~3 |
| `README.md` | Modify (table row) | +~2 / -~2 |
| `CHANGELOG.md` | Modify (Unreleased entry) | +~12 |
| `dist/**` | Regenerate via build script | (gitignored) |

`references/brainstorm-output-schema.md` is **NOT created** in this PR — `references/ai-first-rules.md` already covers vault-note frontmatter and the spec frontmatter requirements (`related_brainstorm`, `spec_path`) are documented inline in `commands/obsidian-brainstorm.md`. (Decision documented in spec OQ-related notes and §6.)

---

## Task 1: Create `references/brainstorm-question-templates.md`

**Spec coverage:** REQ-007.

**Files:**
- Create: `references/brainstorm-question-templates.md`

- [ ] **Step 1: Verify the file does not yet exist**

Run: `ls /Users/leric/Desktop/code/obsidian-second-brain/references/brainstorm-question-templates.md 2>&1`
Expected: `ls: ... No such file or directory`

- [ ] **Step 2: Create the file with full content**

Write this exact content to `/Users/leric/Desktop/code/obsidian-second-brain/references/brainstorm-question-templates.md`:

```markdown
# Brainstorm Question Templates

> Six categories of questions for `/obsidian-brainstorm` Phase 3 iterative Q&A loop. Claude picks one question per turn from these templates (or improvises based on conversation state), preferring multi-choice with `(Other)` over free-text.

This file is referenced by `commands/obsidian-brainstorm.md`. Update both together when adding categories.

## Category 1: Problem Framing

Use early in the loop to disambiguate intent.

**Q: 你 brainstorm 這個的觸發點是什麼?**
- A. 卡在實作,不知道下一步
- B. 不確定方向是否值得做
- C. 收斂多筆 research 成 actionable item
- D. 想 expand scope,看更大的可能性
- E. (Other)

**Q: 目前你最有信心 / 最沒信心的部分?**
- A. 對問題定義有信心,對解法沒信心
- B. 對解法有信心,對問題定義沒信心
- C. 兩者皆無信心
- D. (Other,自由說明)

**Q: 如果這個問題不解決會怎樣?**
- A. 系統會壞 / regression
- B. 工作會變慢 / 機會成本
- C. 機會錯失(競品 / 趨勢)
- D. 沒有實際 impact,只是想做
- E. (Other)

## Category 2: Constraint Surfacing

Use after problem is framed, to bound the solution space.

**Q: 硬限制是?(可複選)**
- A. 必須在 v0.X 前 ship
- B. 不能 break ADR-N
- C. 預算 / 時間有限
- D. 不能改 schema / DB migration
- E. 沒有硬限制
- F. (Other)

**Q: 你願意接受最多多少 LOC 的改動?**
- A. < 100 LOC (minor patch)
- B. 100-500 LOC (medium feature)
- C. 500-2000 LOC (large feature)
- D. 不限 (rewrite OK)

**Q: 誰會看 / 用這個結果?**
- A. 只有我(個人專案)
- B. 小團隊(2-5 人)
- C. 較大團隊 / 外部 contributor
- D. 公開 user / 客戶

## Category 3: Trade-off Forcing

Use when two directions surface that conflict.

**Q: X 路線跟 Y 路線,哪個優先?**
- A. X(犧牲 Y 的 ...)
- B. Y(犧牲 X 的 ...)
- C. 都要(接受複雜度)
- D. 兩者都不對,還有 Z

**Q: 上線時間 vs 完整度,你選哪個?**
- A. 上線快(可接受 50% 完整度,後續迭代)
- B. 完整度高(可接受 delay)
- C. 中庸(70% 完整 + 留 backlog)

**Q: 簡單 + 笨 vs 複雜 + 聰明 的實作?**
- A. 簡單 + 笨,易維護
- B. 複雜 + 聰明,長期更佳
- C. 看情境(請說明)

## Category 4: Scope Bounding

Use late in the loop, to nail in-scope vs out-of-scope.

**Q: 下列哪些 in-scope?(可複選)**
- (Claude 根據 Phase 3 已收斂的議題動態生成 ≥3 個選項)
- (Other)

**Q: 下列哪些明確 out-of-scope?(可複選)**
- (Claude 根據 Phase 3 已收斂的議題動態生成 ≥3 個選項)
- (Other)

**Q: 第一個 MVP 要含什麼?**
- A. 全部(integrated push)
- B. 核心 + 1 個 nice-to-have
- C. 只有核心,nice-to-have 留 backlog
- D. (Other)

## Category 5: Existing-Decision Link

Use when vault scan surfaces a related ADR / Project / past decision.

**Q: 這個方向跟 [[ADR-N]] 是什麼關係?**
- A. 兼容(不影響 ADR-N)
- B. 取代(廢掉 ADR-N)
- C. 修補(在 ADR-N 上加東西)
- D. 開新 ADR(平行)

**Q: 跟現有 [[Projects/X]] 是?**
- A. 獨立(不關聯)
- B. 整合(會修改 X)
- C. 取代 X

**Q: 過去類似的 brainstorm / decision 有哪些?**
- (Claude 列出 Phase 1 vault scan 找到的相關 sessions / ADR)
- (Other / 沒看到我想到的)

## Category 6: Anti-goal

Use before approach proposal, to lock what NOT to build.

**Q: 明確不想做什麼?(自由文字,至少 1 條)**

**Q: 失敗會長怎樣?**
- A. 系統 break
- B. 沒人用
- C. 維護成本爆炸
- D. 跟 ADR-N 衝突
- E. (Other)

**Q: 如果這個 brainstorm 完全沒結論,你會怎樣?**
- A. 沒差,本來就在探索
- B. 浪費時間
- C. 必須有結論才能進下一步

---

## Usage notes for Claude

- **Pick one question per turn.** Do not stack.
- **Multi-choice with `(Other)` is the default.** Use free-text only for `Category 6 Q1` (anti-goals) where multi-choice is too restrictive.
- **Adapt wording** to user's language (zh-TW / en) based on `_CLAUDE.md output-lang`.
- **Re-use categories.** A single Phase 3 may sample from the same category twice if needed; do not feel obligated to cover all 6.
- **Stop sampling when convergence checklist reaches ≥5/6** (per spec REQ-005).
```

- [ ] **Step 3: Verify the file was created with all 6 categories**

Run: `grep -c "^## Category" /Users/leric/Desktop/code/obsidian-second-brain/references/brainstorm-question-templates.md`
Expected: `6`

- [ ] **Step 4: Verify each category has at least 3 example questions**

Run: `awk '/^## Category/{cat=$0; count=0} /^\*\*Q:/{count++} /^## Category/ && NR>1 {print prev, prev_count} {prev=cat; prev_count=count} END{print cat, count}' /Users/leric/Desktop/code/obsidian-second-brain/references/brainstorm-question-templates.md`
Expected: each category shows count ≥3 (Category 1: 3, Category 2: 3, Category 3: 3, Category 4: 3, Category 5: 3, Category 6: 3).

- [ ] **Step 5: Commit**

```bash
git add references/brainstorm-question-templates.md
git commit -m "$(cat <<'EOF'
feat: add brainstorm-question-templates reference for v2

Six question categories (problem-framing, constraint-surfacing,
trade-off-forcing, scope-bounding, existing-decision-link, anti-goal)
each with 3 example questions. Used by /obsidian-brainstorm v2
Phase 3 iterative Q&A loop. Implements spec REQ-007.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Rewrite `commands/obsidian-brainstorm.md`

**Spec coverage:** REQ-001 to REQ-006, REQ-008 to REQ-017.

**Files:**
- Modify: `commands/obsidian-brainstorm.md` (full rewrite of body, preserve frontmatter and Phase 0 parsing)

- [ ] **Step 1: Verify v1 wording is still present (pre-change baseline)**

Run: `grep -c "opening provocations\|4-6 provocations\|drill via follow-ups" /Users/leric/Desktop/code/obsidian-second-brain/commands/obsidian-brainstorm.md`
Expected: ≥1 (v1 wording present)

- [ ] **Step 2: Verify the new wording does NOT exist yet**

Run: `grep -c "Iterative Q&A\|iterative Q&A\|lazy code-fetch" /Users/leric/Desktop/code/obsidian-second-brain/commands/obsidian-brainstorm.md`
Expected: `0`

- [ ] **Step 3: Rewrite the file**

Replace the entire contents of `/Users/leric/Desktop/code/obsidian-second-brain/commands/obsidian-brainstorm.md` with:

````markdown
---
description: Iterative Q&A brainstorm — vault scan, one question at a time (multi-choice preferred), lazy code-fetch on demand, propose 2-3 approaches with trade-off matrix, section-by-section design walk, dual output (engineering spec + vault note)
argument-hint: <repo> [<topic>]
category: thinking
triggers_en: ["brainstorm project", "obsidian brainstorm", "what should I work on", "stuck on next step"]
param-autocomplete:
  - name: repo
    source: vault-projects
  - name: topic
    source: freetext
---

Use the obsidian-second-brain skill. Execute `/obsidian-brainstorm $ARGUMENTS`:

`/obsidian-brainstorm <repo> [<topic>]` runs an iterative Q&A brainstorm modeled after `superpowers:brainstorming`. Phase 0-7 below. Key principles:

- **One question per turn.** Multi-choice preferred. Free-text only when explicitly noted.
- **Lazy code-fetch.** Do not read code upfront; read only when a user answer triggers Case A/B/C (see Phase 3).
- **Section-by-section design.** After approach selection, walk 9 sections one at a time, awaiting user OK per section.
- **Dual output.** Write to both `<repo>/docs/superpowers/specs/<date>-<slug>-design.md` (engineering) and `<vault>/Projects/<repo-slug>/Brainstorms/<date>-<slug>.md` (vault note, AI-first compliant). Bi-directional cross-link required.

Optional flags (carried from v1, may be ignored in v2 — log "ignored in v2" if seen):
- `--lens=...`, `--depth=...`, `--research-window-days=N`, `--lang=zh-TW|en`
- `--topic="<seed>"`: deprecated; honored only when positional `<topic>` is empty (backward compat per commit `66791b1`).

## Phase 0: Parse args + pre-flight

- Confirm vault root has `_CLAUDE.md`. If no, abort with "Run /obsidian-init first."
- Parse `$ARGUMENTS`: first token = `<repo>`, subsequent non-flag tokens joined = `<topic>`, `--flag` tokens kept separate.

```python
import shlex
tokens = shlex.split(args, posix=True)
if not tokens:
    abort("missing <repo> argument. Usage: /obsidian-brainstorm <repo> [<topic>] [--flags]")
repo_token = tokens[0]
rest = tokens[1:]

topic_words = [t for t in rest if not t.startswith('--')]
flag_tokens = [t for t in rest if t.startswith('--')]
topic = " ".join(topic_words).strip()

# Backward-compat: --topic="..." flag is honored only when positional topic is empty
for f in flag_tokens:
    if f.startswith('--topic=') and not topic:
        topic = f.split('=', 1)[1].strip('"').strip("'")

from scripts.commands.repo_resolver import resolve_repo_arg
resolution = resolve_repo_arg(
    repo_token,
    vault_root=Path("~/Documents/SecondBrain").expanduser(),
    allow_global=False,
)

if resolution.state == "project":
    project_dir = resolution.project_dir
    project_slug = resolution.project_slug
    repo_local_path = resolution.local_path  # required for Phase 6 spec write
elif resolution.state == "ambiguous":
    ask_user_to_pick(resolution.candidates)
elif resolution.state in ("unknown", "global"):
    abort(resolution.message)
```

- Confirm `Projects/<project_slug>/` exists. If no, offer `/obsidian-project <P>` or abort.
- Ensure `Projects/<project_slug>/Brainstorms/` exists (`mkdir -p` if missing; notify user).
- Confirm `repo_local_path/docs/superpowers/specs/` exists (`mkdir -p` if missing; notify user).
- Resolve `output_lang` from `_CLAUDE.md` (`zh-TW` or `en`).

## Phase 1: Vault scan (deterministic, no LLM)

Read these in-memory, build a `vault_context` dict. Do NOT read code files in this phase.

1. `Projects/<project_slug>/**/*.md` — all project notes.
2. `Decisions/ADR-*.md` — all ADRs.
3. `Inbox/*.md` — files with mtime within last 30 days.
4. `Logs/YYYY-MM-DD.md` — files with mtime within last 7 days.

Build:

```yaml
vault_context:
  repo_slug: <project_slug>
  related_notes_count: <N>
  recent_decisions: [<ADR-NNN>, ...]
  open_gaps:
    - { topic: "...", source: "Projects/.../foo.md:42" }
  hot_keywords: [...]   # top 10 by frequency in scanned notes
  recent_research_dossiers: <N>   # count from Projects/<P>/Research/
```

`open_gaps` heuristic: notes containing `TODO`, `TBD`, `still investigating`, `不確定`, or `待釐清`. Surface line and source.

For large vaults (>10k notes), scope-limit to the 4 buckets above; do not full-scan.

## Phase 2: Topic discovery (only if `<topic>` is empty)

If `<topic>` is provided, skip Phase 2 and proceed to Phase 3.

If `<topic>` is empty, present **Q1** as a multi-choice question with **≥4 options + `(Other)`**, sourced from `vault_context.open_gaps` and `hot_keywords`:

```
Claude: "我掃了 <N> 篇 vault notes、<M> 個近期 ADR、<K> 份 research dossier。基於這些,以下哪個方向你想 brainstorm?(可複選)

  [ ] A. <gap topic 1>  (from <source>)
  [ ] B. <gap topic 2>  (from <source>)
  [ ] C. <gap topic 3>  (from <source>)
  [ ] D. 從近期 research dossier 收斂出下一個 milestone
  [ ] E. (Other) 我想 brainstorm 別的"
```

If user multi-selects 2+ options, **follow-up Q1.5**: "要從哪個先 drill?" (single-choice from picked items).

**Edge case — `Projects/<repo-slug>/` empty / missing:** Q1 fallback: "我在 vault 找不到 `<repo>` 的紀錄。你想先做 `/obsidian-architect` 還是直接告訴我 topic?"

## Phase 3: Iterative Q&A loop

This is the heart of v2. **Reference `references/brainstorm-question-templates.md`** for the 6-category question library.

### Per-turn structure

1. **Claude asks one question** (multi-choice with `(Other)` preferred; free-text only when explicitly indicated in the template).
2. **User answers.**
3. **Claude shows what was learned** (1-3 lines). May include:
   - **Lazy code-fetch reference:** "根據你選 X,我看了 `src/foo.py:42`,確認 ..."
   - **Vault citation:** "這跟 [[ADR-003]] Update 2026-05-30 一致。"
   - **Contradiction flag:** "但這跟你昨天 [[Logs/2026-05-30]] 寫的 X 有衝突,要釐清嗎?"
4. **Claude updates the convergence checklist** (see below) and decides next action.

### Convergence checklist (internal, 6 items)

After each turn, Claude internally checks:

- [ ] Problem statement clear (1 sentence can name what's being solved)
- [ ] Success criteria clear (how do we know we succeeded)
- [ ] Key constraints surfaced (time / tech / dependency)
- [ ] At least 1 critical trade-off named
- [ ] User intent disambiguated (no two plausible readings)
- [ ] Scope bounded (in-scope and out-of-scope each have ≥1 concrete example)

**Threshold: ≥5/6 → advance to Phase 4.** When 6/6, strongly recommend advancing. User can always interrupt ("propose now") and force-advance regardless of state.

### Lazy code-fetch policy

Default: **do NOT read code in Phase 3.**

Read code only when one of these triggers:

- **Case A:** User answer mentions a specific file / function name → `grep` + read top 1-2 most-relevant files (top 5 by `ripgrep --sort path` if >5 matches; tell user "N more matches available").
- **Case B:** User answer asserts something needing verification (e.g. "我以為 X 已經實裝") → `grep` to verify; if mismatch, surface to user with file:line citation.
- **Case C:** Final sanity check before Phase 4 → read 1-2 core files only.

**Banned:**
- Reading 10+ files at Phase 3 start.
- Reading "for safety" without a specific hypothesis to verify.

### Loop control

- 3 consecutive `(Other)` answers + unclear free-text → Claude proactively says "我有點抓不到方向,要不要 step back 重新問 framing?" (See OQ-1 in spec.)
- User says "propose now" at Q1 → jump to Phase 4 with `(low confidence)` label on approaches.
- User contradicts earlier turn → Claude flags inconsistency: "Q<N> 你說 X,Q<M> 你說 not X,要釐清嗎?"
- Turn count > ~15 → Claude proactively suggests "要不要先 propose approach,不夠再回來?"

## Phase 4: Propose 2-3 approaches

After convergence checklist ≥5/6 (or user force-advance), propose approaches.

### Count rule

- Default: **3 approaches.**
- Minimum: 2 (if Phase 3 strongly converged on one direction).
- Maximum: 3.

### Per-approach structure

Each approach MUST include:

1. **Semantic name** (e.g. "Lazy Backfill", "Strict Schema Extension", "Companion-First Pipeline"). **NEVER** "Approach A / B / C".
2. **1-line elevator pitch.**
3. **3-5 lines of expansion** (how it works).
4. **2-3 pros.**
5. **2-3 cons.**
6. **"What changes in code"** with file paths and approximate LOC scale.
7. **"What stays the same"** (blast-radius framing).

### Trade-off matrix

Render a comparison matrix across all proposed approaches. Dimensions are **derived from constraints surfaced in Phase 3**:

- "Time pressure" → "implementation effort" dimension.
- "ADR-N tension" → "compatible with ADR-N" dimension.
- "Maintenance cost" → "ongoing maintenance" dimension.
- (Do not pad with dimensions Phase 3 didn't surface.)

Matrix MUST appear in the **vault note**. Inclusion in the spec is optional.

### Recommended

**Exactly one** approach MUST be marked `(Recommended)`, with a 1-2 sentence justification grounded in a specific Phase 3 answer.

❌ Forbidden: "All three are fine, you pick."
✅ Required: "(Recommended: <Name>) — 理由:你在 Q<N> 提到 <constraint>,<Name> 在此面向最強。"

### User dissent — Q5

```
Q5: 你選哪個 approach?
  [ ] <Approach 1>
  [ ] <Approach 2> (Recommended)
  [ ] <Approach 3>
  [ ] Modify recommended one (我要在 <Recommended> 上改)
  [ ] None (回 Phase 3 多挖)
```

- **Modify** → short follow-up "要改哪一塊?" (free text + possible code re-verification).
- **None** → return to Phase 3 with a context note explaining why the 3 fell short.

## Phase 5: Section-by-section design walk

Walk the design **9 sections in fixed order**. Present **one section at a time**, await user OK / Modify / back-step before advancing.

**Order:**

1. Problem & Goal (1-2 sentence problem statement + success criteria)
2. Architecture (3-5 sentences + ASCII diagram if needed)
3. Data / Schema (skip if not applicable, mark "N/A")
4. Module / File layout (which files change)
5. Interfaces / APIs (function signatures, event shapes; skip if pure-dialogue design)
6. Edge cases (≥3, each 1 line)
7. Test strategy (unit / integration / smoke, 1-2 sentences each)
8. Out of scope (≥3 explicit exclusions)
9. Open questions (unresolved items, left for implementation or future)

**Per-section presentation format:**

```
Claude: "Section <N> — <Topic>:
        [content, kept tight]

        OK 進下一節 / 改 X / 回上一節?"
```

**Back-step rule:** If user returns to an earlier section and modifies it, Claude MUST re-present the modified section, then walk downstream affected sections labeled "(updated based on your Section N change)".

## Phase 6: Inline self-review + dual write

### Inline self-review (before write, no subagent)

Run all 5 checks:

1. **Placeholder scan:** grep `TBD|TODO|fill in|tbd|implement later|something like|ideally`. Fix inline or promote to Section 9 (Open Questions).
2. **Internal consistency:** function / type / property names across sections — same name = same thing.
3. **Scope check:** out-of-scope items not contradicted elsewhere in the design.
4. **Vault link check:** every referenced ADR / Project / file path — verify it exists via `ls` or `grep`. If not, remove or label `(proposed)`.
5. **Ambiguity scan:** no "something like X", "ideally", "perhaps" hedge words.

Fix inline. Do not re-prompt user.

### Dual write

Write two files:

**1. Engineering spec:**
- Path: `<repo_local_path>/docs/superpowers/specs/<YYYY-MM-DD>-<topic-slug>-design.md`
- Format: follow CLAUDE.md spec convention.
  - REQ-NNN requirements
  - CON-NNN constraints
  - AC-NNN acceptance criteria (Given-When-Then)
  - 11-section template adapted (Goal / Background / Requirements / Constraints / Architecture / File Layout / Edge Cases / Test Strategy / AC / Out of Scope / Open Questions / Success Criteria / References).
- Frontmatter MUST contain:
  ```yaml
  ---
  related_brainstorm: Projects/<repo-slug>/Brainstorms/<date>-<slug>.md
  status: draft
  date: <YYYY-MM-DD>
  author: <user> + Claude (brainstormed via superpowers:brainstorming)
  ---
  ```

**2. Vault note:**
- Path: `<vault>/Projects/<repo-slug>/Brainstorms/<YYYY-MM-DD>-<topic-slug>.md`
- Format: follow `references/ai-first-rules.md` (non-negotiable):
  - `## For future Claude` preamble (zh-TW: `## 給未來 Claude`)
  - Frontmatter: `type: brainstorm`, `date`, `tags`, `ai-first: true`, plus `spec_path:`, `participants:`, `status:`, `topic:`, `project: "[[<project>]]"`, `supersedes_spec:` (if applicable)
  - Wikilinks for every person / project / ADR / file referenced
  - Recency markers per external claim
  - Q&A summary (paraphrased) + key turning-point quotes (verbatim, prefixed with `>`)
  - Phase 4 trade-off matrix (full, even if not in spec)
  - Final approach choice + reason
  - Phase 5 design outline (NOT full content — link to spec)
- Frontmatter MUST contain `spec_path:` pointing to the engineering spec (repo-relative path).

### mkdir on missing target directories

If either target directory doesn't exist, `mkdir -p` and notify user: "I created `<path>`."

### Same-day collision

If a file with the same `<YYYY-MM-DD>-<topic-slug>` already exists at either output path, suffix `-v2`, `-v3`, etc. Never overwrite.

## Phase 7: Handoff

After successful write of both files, offer:

```
Claude: "Spec → <repo>/docs/superpowers/specs/<filename>
        Vault note → Projects/<repo-slug>/Brainstorms/<filename>

        下一步:
        [1] 進 superpowers:writing-plans 產出 implementation plan(推薦)
        [2] 我自己看看,先不要 plan
        [3] 開新 brainstorm topic"
```

- Pick `1` → invoke `superpowers:writing-plans` with `spec: <repo>/docs/superpowers/specs/<filename>`. **Do NOT auto-invoke without explicit user pick.**
- Pick `2` → end.
- Pick `3` → return to Phase 2.

---

**AI-first rule:** The vault note created by this command MUST follow `references/ai-first-rules.md`: `## For future Claude` preamble, rich frontmatter (`type`, `date`, `tags`, `ai-first: true`), recency markers per external claim, mandatory `[[wikilinks]]` for every person / project / ADR / module referenced, sources preserved verbatim, confidence levels where applicable. The engineering spec is repo-side and is NOT subject to AI-first rules.

**Question templates:** See `references/brainstorm-question-templates.md` for the 6 question categories used in Phase 3.

**Language:** Respect `_CLAUDE.md`'s `- output-lang: zh-TW` line by default; honor `--lang=` flag as a single-run override. All prose in chosen language; code identifiers, paths, function names, env vars, and wikilink filename segments remain English regardless.
````

- [ ] **Step 4: Verify v1 wording is gone**

Run: `grep -c "opening provocations\|4-6 provocations\|drill via follow-ups\|ImprovementItems\|distilled-imps" /Users/leric/Desktop/code/obsidian-second-brain/commands/obsidian-brainstorm.md`
Expected: `0`

- [ ] **Step 5: Verify v2 key wording is present**

Run: `grep -c "Iterative Q&A\|lazy code-fetch\|trade-off matrix\|section-by-section\|dual output\|brainstorm-question-templates" /Users/leric/Desktop/code/obsidian-second-brain/commands/obsidian-brainstorm.md`
Expected: ≥6

- [ ] **Step 6: Verify Phase 0 parsing block is preserved (no regression on commit 66791b1)**

Run: `grep -c "import shlex\|tokens\[0\]\|--topic=" /Users/leric/Desktop/code/obsidian-second-brain/commands/obsidian-brainstorm.md`
Expected: ≥3

- [ ] **Step 7: Verify Phase 0-7 headings present**

Run: `grep -E "^## Phase [0-7]:" /Users/leric/Desktop/code/obsidian-second-brain/commands/obsidian-brainstorm.md | wc -l`
Expected: `8`

- [ ] **Step 8: Verify references file is mentioned**

Run: `grep -c "references/brainstorm-question-templates.md\|references/ai-first-rules.md" /Users/leric/Desktop/code/obsidian-second-brain/commands/obsidian-brainstorm.md`
Expected: ≥2

- [ ] **Step 9: Verify no em-dash in command file (per CLAUDE.md convention)**

Run: `grep -c "—" /Users/leric/Desktop/code/obsidian-second-brain/commands/obsidian-brainstorm.md`
Expected: `0`

If non-zero, replace each occurrence with `--` or restructure the sentence.

- [ ] **Step 10: Commit**

```bash
git add commands/obsidian-brainstorm.md
git commit -m "$(cat <<'EOF'
feat: rewrite /obsidian-brainstorm to v2 (iterative Q&A + dual output)

Replace v1 "4-6 opening provocations + drill 1-2" flow with v2
iterative Q&A loop modeled after superpowers:brainstorming:

- Phase 1: vault scan (4 buckets: Projects, Decisions, Inbox/30d, Logs/7d)
- Phase 2: topic discovery (only when <topic> empty); Q1 multi-choice
- Phase 3: one-question-at-a-time loop with 6-item convergence
  checklist (5/6 threshold); lazy code-fetch (Case A/B/C only)
- Phase 4: propose 2-3 approaches with trade-off matrix and forced
  (Recommended); user dissent paths (Modify / None)
- Phase 5: 9-section design walk with per-section OK
- Phase 6: inline self-review + dual write (engineering spec to
  <repo>/docs/superpowers/specs/, vault note to Projects/<P>/Brainstorms/)
  with bi-directional cross-link
- Phase 7: opt-in handoff to superpowers:writing-plans

Preserves Phase 0 positional <repo> [<topic>] parsing from commit 66791b1.
References new references/brainstorm-question-templates.md for Phase 3.

Implements spec REQ-001 through REQ-017 of
docs/superpowers/specs/2026-06-01-obsidian-brainstorm-v2-design.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Sync `SKILL.md` brainstorm description

**Spec coverage:** REQ-018 part 1.

**Files:**
- Modify: `SKILL.md:346` (English commands table row)
- Modify: `SKILL.md:702` (zh-TW description block)

- [ ] **Step 1: Verify current v1 wording is at line 346**

Run: `sed -n '346p' /Users/leric/Desktop/code/obsidian-second-brain/SKILL.md`
Expected output contains: `Interview-style brainstorm — 4-6 provocations`

- [ ] **Step 2: Update SKILL.md line 346 (English table row)**

Replace the line:
```
| `/obsidian-brainstorm <repo> [<topic>]` | Interview-style brainstorm — 4-6 provocations, drill via follow-ups, distill into Brainstorms/ session file. Optional `<topic>` seed focuses provocations; empty topic runs whole-vault gap scan (default) |
```

With:
```
| `/obsidian-brainstorm <repo> [<topic>]` | Iterative Q&A brainstorm — vault scan + one question at a time (multi-choice preferred) + lazy code-fetch + propose 2-3 approaches with trade-off matrix + 9-section design walk + dual output (engineering spec to `<repo>/docs/superpowers/specs/`, vault note to `Projects/<P>/Brainstorms/`). Optional `<topic>` seed; empty topic triggers Phase 2 multi-choice gap-scan discovery |
```

- [ ] **Step 3: Verify line 346 changed**

Run: `grep -c "Iterative Q&A brainstorm.*vault scan" /Users/leric/Desktop/code/obsidian-second-brain/SKILL.md`
Expected: `1`

Run: `grep -c "Interview-style brainstorm.*4-6 provocations" /Users/leric/Desktop/code/obsidian-second-brain/SKILL.md`
Expected: `0`

- [ ] **Step 4: Update SKILL.md line 702 (zh-TW description block)**

Replace the line starting `- /obsidian-brainstorm <repo> [<topic>]` (currently line 702):
```
- `/obsidian-brainstorm <repo> [<topic>]` - 卡住、不知道下一步該做什麼時,interview-style brainstorm。Claude 讀整個 vault(Architecture/* + features + ai-flows + personas + decisions + Research + board + 最近 Logs + 過去 brainstorms)後,丟出 4-6 個大膽的下個方向(混 gap / persona / trend / premortem lens),使用者反應後深挖,蒸餾成 ImprovementItem + 待驗證假設,寫進 `Projects/<P>/Brainstorms/YYYY-MM-DD-<slug>.md`,自動被 `/obsidian-roadmap` 撿走。**`<topic>` 是 optional positional**(對齊 `/obsidian-research(-deep)` 語法):有給 topic 就 focus 在該議題,空 topic 走 whole-vault gap scan(default)。Flags: `--lens` / `--depth=quick|medium|deep` / `--research-window-days` / `--lang` /(deprecated)`--topic="..."`(positional 優先,若 positional 空才 fallback 到 flag)。
```

With:
```
- `/obsidian-brainstorm <repo> [<topic>]` - 卡住、不知道下一步該做什麼時,**iterative Q&A brainstorm**(模仿 `superpowers:brainstorming`)。Phase 1 vault scan(`Projects/<P>` + `Decisions/ADR-*` + `Inbox/30d` + `Logs/7d`),Phase 2 topic discovery(只在 `<topic>` 空時跑,Q1 multi-choice ≥4 + Other),Phase 3 iterative Q&A 一次一問(multi-choice 為主)+ lazy code-fetch + 6-item convergence checklist(5/6 門檻),Phase 4 提 2-3 個 approach + trade-off matrix + 強制 (Recommended),Phase 5 9-section design walk(逐節 approval),Phase 6 inline self-review + **dual output**(engineering spec → `<repo>/docs/superpowers/specs/<date>-<slug>-design.md`,vault note → `Projects/<P>/Brainstorms/<date>-<slug>.md`,雙向 cross-link),Phase 7 opt-in handoff 到 `superpowers:writing-plans`。Positional `<topic>` 為主,`--topic="..."` deprecated 但 backward-compat 保留。詳見 `references/brainstorm-question-templates.md`(Phase 3 問題模板)與 `references/ai-first-rules.md`(vault note 格式)。
```

- [ ] **Step 5: Verify zh-TW block updated**

Run: `grep -c "iterative Q&A brainstorm\|9-section design walk\|dual output" /Users/leric/Desktop/code/obsidian-second-brain/SKILL.md`
Expected: ≥3

Run: `grep -c "interview-style brainstorm\|4-6 個大膽的下個方向" /Users/leric/Desktop/code/obsidian-second-brain/SKILL.md`
Expected: `0`

- [ ] **Step 6: Commit**

```bash
git add SKILL.md
git commit -m "$(cat <<'EOF'
docs: sync SKILL.md brainstorm description to v2

Update both the English commands table row (line ~346) and the zh-TW
description block (line ~702) to reflect the v2 iterative Q&A flow,
dual output (engineering spec + vault note), and Phase 1-7 structure.

Implements spec REQ-018 part 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Sync `README.md` commands table row

**Spec coverage:** REQ-018 part 2.

**Files:**
- Modify: `README.md:290`

- [ ] **Step 1: Verify v1 README wording**

Run: `sed -n '290p' /Users/leric/Desktop/code/obsidian-second-brain/README.md`
Expected output contains: `4-6 個大膽方向`

- [ ] **Step 2: Update line 290**

Replace:
```
| `/obsidian-brainstorm <repo> [<topic>]` | 卡住、不知道下一步該做什麼時,Claude 訪談式 brainstorm,丟 4-6 個大膽方向,使用者反應後深挖,蒸餾成 roadmap 候選。Optional `<topic>` seed focus 在指定議題;空 topic 走 whole-vault gap scan(default) |
```

With:
```
| `/obsidian-brainstorm <repo> [<topic>]` | Iterative Q&A brainstorm(模仿 `superpowers:brainstorming`):vault scan + 一次一問 + lazy code-fetch + 2-3 個 approach + trade-off matrix + 9-section 逐節 design + dual output(engineering spec + vault note,雙向 cross-link)+ opt-in handoff 到 `writing-plans`。Optional `<topic>` seed;空 topic 觸發 Phase 2 multi-choice gap discovery |
```

- [ ] **Step 3: Verify**

Run: `grep -c "Iterative Q&A brainstorm.*superpowers:brainstorming" /Users/leric/Desktop/code/obsidian-second-brain/README.md`
Expected: `1`

Run: `grep -c "4-6 個大膽方向\|訪談式 brainstorm" /Users/leric/Desktop/code/obsidian-second-brain/README.md`
Expected: `0`

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: sync README.md brainstorm row to v2

Update the /obsidian-brainstorm row in the commands table to reflect
the v2 iterative Q&A flow + dual output + writing-plans handoff.

Implements spec REQ-018 part 2.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add `CHANGELOG.md` Unreleased entry for v2

**Spec coverage:** REQ-018 part 3.

**Files:**
- Modify: `CHANGELOG.md` (insert new section under `## [Unreleased]`, BEFORE the existing `### Changed (brainstorm topic as positional argument)` section)

- [ ] **Step 1: Verify CHANGELOG state — existing entry is the topic-positional change**

Run: `head -25 /Users/leric/Desktop/code/obsidian-second-brain/CHANGELOG.md`
Expected: shows `## [Unreleased]` followed by `### Changed (brainstorm topic as positional argument)`.

- [ ] **Step 2: Insert the new v2 entry above the existing brainstorm entry**

Use Edit to replace the existing block:

Old string:
```
## [Unreleased]

### Changed (brainstorm topic as positional argument)
```

New string:
```
## [Unreleased]

### Changed (brainstorm v2 — iterative Q&A, dual output, lazy code-fetch)

- `/obsidian-brainstorm` Phase 1-7 flow re-designed to mimic
  `superpowers:brainstorming`. Replaces the v1 "4-6 opening
  provocations + drill 1-2" with one-question-at-a-time iterative Q&A,
  multi-choice preferred, lazy code-fetch (Case A/B/C only), 6-item
  convergence checklist with 5/6 threshold, 2-3 approach proposal with
  trade-off matrix and forced `(Recommended)`, 9-section
  section-by-section design walk with per-section approval, inline
  self-review.
- **Dual output:** engineering spec written to
  `<repo>/docs/superpowers/specs/<date>-<slug>-design.md` (REQ/CON/AC
  IDs, consumable by `superpowers:writing-plans`); vault note written
  to `Projects/<P>/Brainstorms/<date>-<slug>.md` (AI-first compliant,
  with Q&A summary, key turning-point quotes, trade-off matrix). Both
  files bi-directionally cross-linked via frontmatter
  (`related_brainstorm:` ↔ `spec_path:`).
- New reference file `references/brainstorm-question-templates.md` with
  6 question categories (problem-framing, constraint-surfacing,
  trade-off-forcing, scope-bounding, existing-decision-link, anti-goal).
- Phase 7 offers opt-in handoff to `superpowers:writing-plans`;
  command does NOT auto-chain.
- Positional `<repo> [<topic>]` argument shape preserved (commit
  `66791b1`).
- Spec: `docs/superpowers/specs/2026-06-01-obsidian-brainstorm-v2-design.md`
- Supersedes the v1 design at
  `docs/superpowers/specs/2026-05-29-obsidian-brainstorm-design.md`.

### Changed (brainstorm topic as positional argument)
```

- [ ] **Step 3: Verify**

Run: `grep -c "brainstorm v2 — iterative Q&A" /Users/leric/Desktop/code/obsidian-second-brain/CHANGELOG.md`
Expected: `1`

Run: `grep -c "Dual output\|brainstorm-question-templates.md\|writing-plans" /Users/leric/Desktop/code/obsidian-second-brain/CHANGELOG.md`
Expected: ≥3

- [ ] **Step 4: Verify ordering — v2 entry comes BEFORE topic-positional entry**

Run: `awk '/^### Changed/{print NR": "$0}' /Users/leric/Desktop/code/obsidian-second-brain/CHANGELOG.md | head -5`
Expected: first `### Changed` line contains "brainstorm v2"; second `### Changed` line contains "brainstorm topic as positional".

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs: add CHANGELOG entry for /obsidian-brainstorm v2

Document the v2 iterative Q&A redesign, dual output, lazy code-fetch,
new question templates reference, and opt-in writing-plans handoff
under [Unreleased].

Implements spec REQ-018 part 3.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Rebuild adapters

**Spec coverage:** REQ-019.

**Files:**
- Run: `bash scripts/build.sh` (regenerates `dist/` for all 4 platforms; gitignored)

- [ ] **Step 1: Run the full multi-platform build**

Run: `cd /Users/leric/Desktop/code/obsidian-second-brain && bash scripts/build.sh`
Expected: exits with code 0; prints success for `claude-code`, `codex-cli`, `gemini-cli`, `opencode`.

- [ ] **Step 2: Verify all 4 dist directories exist**

Run: `ls -d /Users/leric/Desktop/code/obsidian-second-brain/dist/claude-code /Users/leric/Desktop/code/obsidian-second-brain/dist/codex-cli /Users/leric/Desktop/code/obsidian-second-brain/dist/gemini-cli /Users/leric/Desktop/code/obsidian-second-brain/dist/opencode`
Expected: all 4 paths listed, no "No such file or directory" errors.

- [ ] **Step 3: Verify the rewritten brainstorm command is in each adapter's output**

Run: `for p in claude-code codex-cli gemini-cli opencode; do
  echo "=== $p ==="
  find /Users/leric/Desktop/code/obsidian-second-brain/dist/$p -name '*brainstorm*' -type f | head -3
done`
Expected: each platform produces at least one brainstorm-related file.

- [ ] **Step 4: Verify v2 wording present in each adapter's brainstorm artifact**

Run: `for p in claude-code codex-cli gemini-cli opencode; do
  echo "=== $p ==="
  grep -l "Iterative Q&A\|lazy code-fetch" /Users/leric/Desktop/code/obsidian-second-brain/dist/$p -r 2>/dev/null | head -2
done`
Expected: each platform shows ≥1 file containing the v2 wording.

- [ ] **Step 5: Verify routing table in non-claude-code adapters mentions brainstorm with new description**

Run: `grep -h "obsidian-brainstorm" /Users/leric/Desktop/code/obsidian-second-brain/dist/codex-cli/AGENTS.md /Users/leric/Desktop/code/obsidian-second-brain/dist/gemini-cli/GEMINI.md /Users/leric/Desktop/code/obsidian-second-brain/dist/opencode/AGENTS.md 2>/dev/null | head -6`
Expected: each line mentions "Iterative Q&A" or "iterative Q&A brainstorm".

- [ ] **Step 6: No commit needed (dist/ is gitignored)**

Confirm via:
Run: `cd /Users/leric/Desktop/code/obsidian-second-brain && git status --porcelain dist/`
Expected: empty output (no tracked changes in `dist/`).

---

## Task 7: Tier 1 smoke verification (manual, by maintainer in Claude Code)

**Spec coverage:** SC-1 success criterion. AC-001 to AC-015 conceptually.

This task is **NOT executable inside the implementation session**. It requires invoking `/obsidian-brainstorm` in a Claude Code REPL against this repo itself (meta-case smoke). The maintainer (Eugeniu) runs this protocol after implementation lands.

**Files:**
- No files modified. Verification only.

- [ ] **Step 1: Reload the skill (symlinked install)**

If using the `install.sh` symlink approach, no action needed (changes are live).

If installed via copy, run: `bash install.sh` to refresh.

- [ ] **Step 2: Invoke the command on this repo**

In a fresh Claude Code session at `/Users/leric/Desktop/code/obsidian-second-brain`:

```
/obsidian-brainstorm /Users/leric/Desktop/code/obsidian-second-brain
```

(Empty topic — exercises Phase 2 topic discovery.)

- [ ] **Step 3: Verify Phase 0-7 all execute**

During the session, confirm each phase fires:

```
[ ] Phase 0: parse + pre-flight (mkdir notifications if directories were absent)
[ ] Phase 1: vault scan reports related_notes_count, recent_decisions, etc.
[ ] Phase 2: Q1 presented as multi-choice with ≥4 options + (Other)
[ ] Phase 2.5 (if multi-select): follow-up "which first?" question
[ ] Phase 3: ≥3 iterative Q&A turns, multi-choice preferred
[ ] Phase 3 lazy code-fetch: zero file reads BEFORE first user answer triggers Case A/B/C
[ ] Phase 4: 2-3 approaches with semantic names, trade-off matrix, exactly one (Recommended)
[ ] Phase 5: 9 sections walked one at a time
[ ] Phase 6: inline self-review (no subagent invocation), both files written
[ ] Phase 7: 3-option handoff offered
```

- [ ] **Step 4: Verify dual output files exist with correct paths**

Run: `ls /Users/leric/Desktop/code/obsidian-second-brain/docs/superpowers/specs/2026-06-01-*-design.md /Users/leric/Documents/SecondBrain/Projects/obsidian-second-brain/Brainstorms/2026-06-01-*.md 2>&1 | head -10`
Expected: both paths exist with today's date prefix and matching slug.

- [ ] **Step 5: Verify bi-directional cross-link**

Run:
```bash
SPEC=$(ls /Users/leric/Desktop/code/obsidian-second-brain/docs/superpowers/specs/2026-06-01-*-design.md | tail -1)
NOTE=$(ls /Users/leric/Documents/SecondBrain/Projects/obsidian-second-brain/Brainstorms/2026-06-01-*.md | tail -1)
echo "--- spec frontmatter ---"
head -10 "$SPEC"
echo "--- note frontmatter ---"
head -15 "$NOTE"
```
Expected:
- Spec frontmatter contains `related_brainstorm:` pointing to a path under `Projects/obsidian-second-brain/Brainstorms/`.
- Note frontmatter contains `spec_path:` pointing to a path under `docs/superpowers/specs/`.
- The two paths reference each other.

- [ ] **Step 6: AI-first compliance for vault note**

In Claude Code, run:
```
/obsidian-health
```
Filter output for the new vault note. Expected: passes all 7 rules — frontmatter present, `ai-first: true`, `## For future Claude` preamble, ≥1 wikilink, tags non-empty, date = today, no emoji (unless explicit UI), no em-dash.

- [ ] **Step 7: REQ-014 / AC-013 manual check — bi-directional cross-link integrity**

Open the spec frontmatter. Confirm `related_brainstorm:` value exactly matches the vault note's relative path.
Open the vault note frontmatter. Confirm `spec_path:` value exactly matches the spec's relative path.

- [ ] **Step 8: Spec has REQ-NNN / AC-NNN IDs**

Run: `grep -c "^### REQ-\|^### AC-" "$SPEC"`
Expected: ≥10 (enough REQ + AC IDs to be `writing-plans`-consumable).

- [ ] **Step 9: Vault note has `## For future Claude` preamble + key quotes**

Run: `grep -c "^## For future Claude\|^## 給未來 Claude" "$NOTE"`
Expected: `1`

Run: `grep -c "^> " "$NOTE"`
Expected: ≥3 (key turning-point quotes from Phase 3/4).

- [ ] **Step 10: Document smoke result in CHANGELOG**

If smoke passes cleanly, no action.
If smoke surfaces issues, file each as a follow-up task and either fix-and-recommit on this branch or open issues.

- [ ] **Step 11: Phase 7 handoff option 1 produces a writing-plans plan**

In the Claude Code session, when Phase 7 offers options, pick `1`. Verify that `superpowers:writing-plans` invokes successfully with the spec path and produces an implementation plan under `docs/superpowers/plans/`.

This step exercises SC-2 (the spec is `writing-plans`-consumable).

---

## Self-Review

After writing the plan above, verify the following against the spec.

### 1. Spec coverage

| Spec ID | Implemented by |
|---|---|
| REQ-001 (positional arg) | Task 2 Step 3 (Phase 0 preserved); Task 2 Step 6 (regression grep) |
| REQ-002 (vault scan Phase 1) | Task 2 Step 3 (Phase 1 section) |
| REQ-003 (topic discovery Phase 2) | Task 2 Step 3 (Phase 2 section) |
| REQ-004 (iterative Q&A loop) | Task 2 Step 3 (Phase 3 section) |
| REQ-005 (convergence checklist 5/6) | Task 2 Step 3 (Phase 3 / checklist subsection) |
| REQ-006 (lazy code-fetch Case A/B/C) | Task 2 Step 3 (Phase 3 / lazy fetch subsection) |
| REQ-007 (question template library) | Task 1 |
| REQ-008 (approach proposal 2-3) | Task 2 Step 3 (Phase 4 / count rule) |
| REQ-009 (trade-off matrix) | Task 2 Step 3 (Phase 4 / matrix subsection) |
| REQ-010 (forced Recommended) | Task 2 Step 3 (Phase 4 / Recommended subsection) |
| REQ-011 (user dissent paths) | Task 2 Step 3 (Phase 4 / Q5 dissent) |
| REQ-012 (section-by-section walk) | Task 2 Step 3 (Phase 5) |
| REQ-013 (inline self-review) | Task 2 Step 3 (Phase 6 / self-review subsection) |
| REQ-014 (dual output) | Task 2 Step 3 (Phase 6 / dual write); Task 7 Step 4-5 |
| REQ-015 (mkdir missing dirs) | Task 2 Step 3 (Phase 0 + Phase 6 mkdir mentions) |
| REQ-016 (collision suffix) | Task 2 Step 3 (Phase 6 / collision subsection) |
| REQ-017 (Phase 7 handoff) | Task 2 Step 3 (Phase 7) |
| REQ-018 (skill doc sync) | Tasks 3 (SKILL.md), 4 (README.md), 5 (CHANGELOG.md) |
| REQ-019 (adapter rebuild) | Task 6 |
| CON-001 (no test framework) | Honored — TDD adaptation in plan preamble; no pytest/jest added |
| CON-002 (no Python in commands/*.md) | Honored — Phase 0 keeps existing pseudo-code shape (LLM-procedure); no new Python module |
| CON-003 (backward-compat --topic=) | Task 2 Step 6 (parsing block preserved with `--topic=` handling) |
| CON-004 (single repo) | Implicit — no multi-repo logic added |
| CON-005 (no state persistence) | Implicit — no session file written mid-flow |
| CON-006 (AI-first for vault note only) | Task 2 Step 3 (Phase 6 / ai-first reference) |
| CON-007 (dist gitignored) | Task 6 Step 6 (verify no dist/ changes staged) |
| AC-001 to AC-015 | Task 7 (smoke covers each) |
| SC-1 (smoke produces dual output) | Task 7 Step 4 |
| SC-2 (spec writing-plans-consumable) | Task 7 Step 11 |
| SC-3 (vault note passes /obsidian-health) | Task 7 Step 6 |
| SC-4 (self-assessment) | Task 7 Step 10 (informal, by maintainer) |
| SC-5 (4 adapters rebuild clean) | Task 6 |

**No gaps identified.**

### 2. Placeholder scan

- No "TBD", "TODO" (other than in grep targets where they're search terms), "fill in", "implement later" in plan body.
- Every code/markdown step contains actual content.
- Every verification step has an exact command and expected output.

### 3. Type consistency

- `vault_context` dict shape consistent across Phase 1 description and Task 2 Step 3.
- `project_slug` / `repo_local_path` named consistently across Phase 0 and Phase 6 references.
- `<repo-slug>` / `<topic-slug>` placeholders used consistently in path templates.
- Phase numbering 0-7 consistent.
- Convergence checklist always 6 items, threshold always 5/6.
- Approach count always 2-3 (default 3, min 2).

No inconsistencies found.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-01-obsidian-brainstorm-v2-impl.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

**Which approach?**
