---
description: Iterative Q&A brainstorm -- vault scan, one question at a time (multi-choice preferred), lazy code-fetch on demand, propose 2-3 approaches with trade-off matrix, section-by-section design walk, dual output (engineering spec + vault note)
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

`/obsidian-brainstorm <repo> [<topic>]` runs an iterative Q&A brainstorm modeled after `superpowers:brainstorming`. Phase 0-7 below. Iterative Q&A key principles:

- **One question per turn.** Multi-choice preferred. Free-text only when explicitly noted.
- **Lazy code-fetch.** Do not read code upfront; read only when a user answer triggers Case A/B/C (see Phase 3).
- **Section-by-section design.** After approach selection, walk 9 sections one at a time, awaiting user OK per section.
- **Dual output.** Write to both `<repo>/docs/superpowers/specs/<date>-<slug>-design.md` (engineering) and `<vault>/Projects/<repo-slug>/Brainstorms/<date>-<slug>.md` (vault note, AI-first compliant). Bi-directional cross-link required.

Optional flags (carried from v1, may be ignored in v2 -- log "ignored in v2" if seen):
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

1. `Projects/<project_slug>/**/*.md` -- all project notes.
2. `Decisions/ADR-*.md` -- all ADRs.
3. `Inbox/*.md` -- files with mtime within last 30 days.
4. `Logs/YYYY-MM-DD.md` -- files with mtime within last 7 days.

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

**Edge case -- `Projects/<repo-slug>/` empty / missing:** Q1 fallback: "我在 vault 找不到 `<repo>` 的紀錄。你想先做 `/obsidian-architect` 還是直接告訴我 topic?"

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
✅ Required: "(Recommended: <Name>) -- 理由:你在 Q<N> 提到 <constraint>,<Name> 在此面向最強。"

### User dissent -- Q5

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
Claude: "Section <N> -- <Topic>:
        [content, kept tight]

        OK 進下一節 / 改 X / 回上一節?"
```

**Back-step rule:** If user returns to an earlier section and modifies it, Claude MUST re-present the modified section, then walk downstream affected sections labeled "(updated based on your Section N change)".

## Phase 6: Inline self-review + dual write

### Inline self-review (before write, no subagent)

Run all 5 checks:

1. **Placeholder scan:** grep `TBD|TODO|fill in|tbd|implement later|something like|ideally`. Fix inline or promote to Section 9 (Open Questions).
2. **Internal consistency:** function / type / property names across sections -- same name = same thing.
3. **Scope check:** out-of-scope items not contradicted elsewhere in the design.
4. **Vault link check:** every referenced ADR / Project / file path -- verify it exists via `ls` or `grep`. If not, remove or label `(proposed)`.
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
  - Phase 5 design outline (NOT full content -- link to spec)
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
