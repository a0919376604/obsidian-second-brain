---
related_brainstorm: Projects/obsidian-second-brain/Brainstorms/2026-06-01-obsidian-brainstorm-v2.md
status: draft
date: 2026-06-01
author: Eugeniu + Claude (brainstormed via superpowers:brainstorming)
supersedes: docs/superpowers/specs/2026-05-29-obsidian-brainstorm-design.md
---

# `/obsidian-brainstorm` v2 Design — Iterative Q&A + Dual Output

## 1. Goal

Re-design `/obsidian-brainstorm` so it stops emitting low-quality monolithic reports. v2 mimics the `superpowers:brainstorming` flow: one question at a time, multi-choice preferred, lazy code-fetch as needed, then propose 2-3 approaches with a trade-off matrix, then a section-by-section design walk, then write to **two destinations** (engineering spec + vault note) with cross-links.

Supersedes the v1 design at `docs/superpowers/specs/2026-05-29-obsidian-brainstorm-design.md` (4-6 opening provocations + drill 1-2). The argument-positional `<repo> [<topic>]` shape from commit `66791b1` is preserved.

## 2. Background — Why v2

**v1 problems (observed during dogfooding):**
- Opening provocations dump 4-6 directions at once; user feels overwhelmed, picks one, the other 5 are wasted.
- Claude rarely reads code during the conversation, so suggestions are speculative.
- Output is a single vault note; downstream `superpowers:writing-plans` cannot consume it.
- Final report often reads as filler, not actionable.

**v2 thesis:** Apply the proven `superpowers:brainstorming` shape — iterative single questions, multi-choice answers, evidence-driven (lazy code-fetch), section-by-section design with user approval — and emit **both** an engineering spec (REQ/CON/AC IDs, for `writing-plans`) and a vault note (AI-first format, for future-Claude retrieval).

## 3. Requirements

### REQ-001 — Positional argument shape
The command MUST accept `/obsidian-brainstorm <repo> [<topic>]` with backward-compat for `--topic="..."` flag (used only when positional `<topic>` is empty). Behavior aligns with commit `66791b1`.

### REQ-002 — Vault scan as Phase 1
The command MUST always run a vault scan in Phase 1 covering:
- `Projects/<repo-slug>/**/*.md`
- `Decisions/ADR-*.md`
- `Inbox/*.md` from the last 30 days
- `Logs/*.md` from the last 7 days

Output: an in-memory `vault_context` with related_notes_count, recent_decisions, open_gaps (heuristic: notes containing `TODO` / `TBD` / "still investigating"), hot_keywords, recent_research_dossiers count.

### REQ-003 — Topic discovery (Phase 2)
If `<topic>` is empty, Phase 2 MUST trigger and present Q1 as a multi-choice question with **≥4 options**, sourced from `vault_context.open_gaps` and `hot_keywords`. The final option MUST be `(Other)` for free-text fallback. Multi-select MUST be allowed. After multi-select, a follow-up question MUST ask the user to order the picked topics.

If `<topic>` is provided, Phase 2 MUST be skipped.

### REQ-004 — Iterative Q&A loop (Phase 3)
Phase 3 MUST follow a one-question-at-a-time loop. Each turn:
1. Claude asks one question (multi-choice preferred, with `(Other)`).
2. User answers.
3. Claude shows what was learned (1-3 lines, possibly with lazy code-fetch reference or vault citation or contradiction flag).
4. Claude decides whether to continue or break to Phase 4 based on the convergence checklist (REQ-005).

### REQ-005 — Convergence checklist
The command MUST maintain a 6-item internal checklist:
- Problem statement clear
- Success criteria clear
- Key constraints surfaced
- At least 1 critical trade-off named
- User intent disambiguated
- Scope bounded (in / out each with at least 1 example)

Phase 3 MUST stay in loop until **≥5/6** checklist items are checked. When all 6 are checked, advancing to Phase 4 is strongly recommended. The user MUST always be able to interrupt the loop ("dyou propose now") and force advance regardless of checklist state.

### REQ-006 — Lazy code-fetch policy
The command MUST NOT read code upfront in Phase 3. Code reads are permitted only in three cases:
- **Case A:** User answer mentions a specific file/function name → grep + read top 1-2 most-relevant files.
- **Case B:** User answer asserts something that needs verification → grep to verify; if mismatch, surface to user.
- **Case C:** Final sanity check before Phase 4 → read 1-2 core files only.

Banned:
- Reading 10+ files at Phase 3 start.
- Reading "for safety" without a specific hypothesis to verify.

### REQ-007 — Question template library
A new file `references/brainstorm-question-templates.md` MUST be created containing 6 question categories: problem-framing, constraint-surfacing, trade-off-forcing, scope-bounding, existing-decision-link, anti-goal. Each category MUST contain 3-5 concrete example questions. `commands/obsidian-brainstorm.md` MUST reference this file.

### REQ-008 — Approach proposal (Phase 4)
Phase 4 MUST propose **2-3** approaches (default 3; minimum 2 if Phase 3 strongly converged on one direction). Each approach MUST include:
- 1-line elevator pitch
- 3-5 lines of expansion
- 2-3 pros
- 2-3 cons
- 1 "what changes in code" with file paths and approximate LOC scale
- 1 "what stays the same" (blast-radius framing)

Approaches MUST use semantic names (e.g. "Lazy Backfill", not "Approach A").

### REQ-009 — Trade-off matrix
Phase 4 MUST present a comparison matrix across all proposed approaches. The matrix dimensions MUST be derived from constraints surfaced in Phase 3 (e.g. "time pressure" → "implementation effort" dimension; "ADR-N tension" → "compatible with ADR-N" dimension). The matrix MUST appear in the vault note; inclusion in the spec is optional.

### REQ-010 — Recommended approach
Phase 4 MUST mark exactly one approach as `(Recommended)`, with a 1-2 sentence justification grounded in Phase 3 answers. "All three are fine, you pick" is forbidden.

### REQ-011 — User dissent paths
The Q5 (approach choice) MUST offer: each approach, `Modify recommended one`, and `None (return to Phase 3)`. Modify → short follow-up "what to change?" with possible code re-verification. None → return to Phase 3 with context of why the 3 approaches fell short.

### REQ-012 — Section-by-section design walk (Phase 5)
Phase 5 MUST walk the design in this fixed order, presenting one section at a time and awaiting user OK / Modify / back-step before advancing:
1. Problem & Goal
2. Architecture
3. Data / Schema (skip if not applicable)
4. Module / File layout
5. Interfaces / APIs
6. Edge cases (≥3)
7. Test strategy
8. Out of scope (≥3)
9. Open questions

User MUST be able to return to a previous section. On return, Claude MUST re-present that section with updates and surface any downstream sections affected.

### REQ-013 — Inline self-review
Before Phase 6 writes, Claude MUST run an inline self-review (no subagent dispatch) covering:
- Placeholder scan (grep `TBD|TODO|fill in|tbd`)
- Internal consistency (function/type/property names across sections)
- Scope check (out-of-scope items not contradicted elsewhere)
- Vault link check (referenced ADR / Project paths actually exist)
- Ambiguity scan (no "something like", "ideally", etc.)

Issues MUST be fixed inline without re-prompting the user. If a placeholder cannot be resolved due to missing information, it MUST be promoted to Section 9 (Open Questions).

### REQ-014 — Dual output
Phase 6 MUST write two files:

**Engineering spec** (engineering-facing, for `writing-plans`):
- Path: `<repo>/docs/superpowers/specs/<YYYY-MM-DD>-<topic-slug>-design.md`
- Format: follow CLAUDE.md spec convention (REQ-NNN / CON-NNN / AC-NNN IDs, Given-When-Then acceptance criteria where applicable, 11-section template adapted)
- Frontmatter MUST contain `related_brainstorm:` pointing to the vault note.

**Vault note** (memory-facing, for future-Claude retrieval):
- Path: `<vault>/Projects/<repo-slug>/Brainstorms/<YYYY-MM-DD>-<topic-slug>.md`
- Format: follow `references/ai-first-rules.md` (frontmatter with `type: brainstorm` and `ai-first: true`, `## For future Claude` preamble, wikilinks, recency markers)
- MUST contain a Q&A summary (摘要 + key turning-point quotes verbatim), Phase 4 trade-off matrix in full, final approach choice with reason, Phase 5 design outline (not full content — link to spec instead).
- Frontmatter MUST contain `spec_path:` pointing to the engineering spec.

Cross-link bi-directional integrity is non-negotiable.

### REQ-015 — Mkdir on missing target directories
If `<repo>/docs/superpowers/specs/` or `<vault>/Projects/<repo-slug>/Brainstorms/` does not exist, Phase 6 MUST `mkdir -p` and notify the user "I created this directory."

### REQ-016 — Same-day collision handling
If a file with the same `<YYYY-MM-DD>-<topic-slug>` already exists (second brainstorm same day on same topic), Phase 6 MUST suffix `-v2`, `-v3`, etc., and never overwrite.

### REQ-017 — Phase 7 handoff
After successful write, Phase 7 MUST offer three options:
- Proceed to `superpowers:writing-plans` (recommended).
- Just save, no plan yet.
- Start a new brainstorm topic.

The command MUST NOT auto-invoke `writing-plans`. User explicit choice required.

### REQ-018 — Skill documentation sync
The PR MUST update:
- `SKILL.md` Layer 2 brainstorm row + zh-TW description block.
- `README.md` commands table row for brainstorm.
- `CHANGELOG.md` `## [Unreleased]` entry: "Changed (brainstorm v2 — iterative Q&A, dual output, lazy code-fetch)".

### REQ-019 — Adapter rebuild
After editing `commands/obsidian-brainstorm.md`, the PR MUST run `bash scripts/build.sh` and verify all 4 adapters (claude-code / codex-cli / gemini-cli / opencode) build clean.

## 4. Constraints

### CON-001 — No new test framework
This PR does NOT introduce pytest / jest / etc. The repo has no automated test suite; v2 keeps verification manual.

### CON-002 — No code in commands/*.md
The skill is markdown instruction, not Python. Phase logic is described as procedure for the LLM to follow, not as executable code. Python helpers are out of scope for this PR.

### CON-003 — Backward-compat with `--topic="..."` flag
The legacy `--topic=` flag MUST still work, but only when positional `<topic>` is empty.

### CON-004 — Single repo per invocation
The command does NOT support multi-repo brainstorm. One repo per invocation. Cross-repo ideas → separate invocations.

### CON-005 — No conversational state persistence
Mid-brainstorm interruption does NOT support resume. Session lives within one Claude Code conversation.

### CON-006 — AI-first compliance for vault writes only
Vault notes MUST pass `references/ai-first-rules.md`. The engineering spec is repo-side and is NOT subject to AI-first rules.

### CON-007 — Build output is gitignored
`dist/` MUST NOT be committed. Only `commands/`, `references/`, and source files are tracked.

## 5. Architecture

```
/obsidian-brainstorm <repo> [<topic>]
        │
        ▼
   Phase 0: Parse args (shlex; positional <repo> + <topic>, --topic= fallback)
        │
        ▼
   Phase 1: Vault scan (Projects/<repo-slug>, Decisions/, Inbox/30d, Logs/7d)
        │
        ▼
   Phase 2: Topic discovery (only if <topic> empty; Q1 multi-choice ≥4 + Other)
        │
        ▼
   Phase 3: Q&A loop ─────────────────────────────────┐
        │   one Q at a time, multi-choice preferred  │
        │   lazy code-fetch (Case A/B/C only)        │
        │   convergence checklist 6 items, ≥5/6     │
        └──── until checklist ≥5/6 or user breaks ──┘
        │
        ▼
   Phase 4: Propose 2-3 approaches + trade-off matrix + (Recommended)
        │
        ▼
   Phase 5: Section-by-section design (9 sections, user OK per section)
        │
        ▼
   Inline self-review (placeholder/consistency/scope/vault-link/ambiguity)
        │
        ▼
   Phase 6: Dual write
        ├─ <repo>/docs/superpowers/specs/<date>-<slug>-design.md
        └─ <vault>/Projects/<repo-slug>/Brainstorms/<date>-<slug>.md
        │
        ▼
   Phase 7: Handoff (writing-plans / save-only / new-brainstorm)
```

## 6. File Layout

### Modify

| File | Change |
|---|---|
| `commands/obsidian-brainstorm.md` | Rewrite Phase 0-7 procedure; remove v1 "opening provocations" entirely; reference `references/brainstorm-question-templates.md` and `references/ai-first-rules.md`; preserve positional `<repo> [<topic>]` argument shape from commit `66791b1`. Approx +200 / -100 LOC. |
| `SKILL.md` | Update Layer 2 thinking-tools row (line ~346) and zh-TW description block (line ~702) to reflect iterative Q&A + dual output. ~5 lines added / 3 removed. |
| `README.md` | Update brainstorm row in commands table (line ~290). ~2 lines changed. |
| `CHANGELOG.md` | Add `## [Unreleased]` entry: "Changed (brainstorm v2 — iterative Q&A, dual output, lazy code-fetch)". ~10 lines. |

### Create

| File | Purpose |
|---|---|
| `references/brainstorm-question-templates.md` | 6 question categories × 3-5 examples each. Referenced by `commands/obsidian-brainstorm.md`. Approx 120 LOC. |
| `references/brainstorm-output-schema.md` (optional) | Defines spec + vault-note frontmatter schema and cross-link rules. **Decision deferred to implementation:** if `references/ai-first-rules.md` already covers it, skip this file. Approx 60 LOC if created. |

### Do not modify

- `scripts/` — no Python helper introduced.
- `adapters/` — regenerated automatically by `bash scripts/build.sh`.
- `hooks/`, `install.sh` — unrelated.
- `dist/` — gitignored; rebuilt only.

### Estimated total change: ~400 LOC, single PR.

## 7. Edge Cases

### Phase 0 (argument parsing)
- Missing `<repo>` → abort with usage hint.
- `<repo>` path not found → abort with explicit message.
- `<repo>` is not a git repo → warn and continue.
- `<topic>` contains special chars (`"`, `/`, `#`) → handled by shlex.
- Legacy flags `--lens=` `--depth=` → log "ignored in v2" warning, continue.

### Phase 1 (vault scan)
- Vault path unconfigured → abort with "run `/obsidian-init` first".
- Vault > 10k notes → scope-limit scan to `Projects/<repo-slug>/`, `Decisions/`, last 7 days `Logs/`.
- Empty vault → continue to Phase 3 with Q1 = "vault is empty, basic framing questions follow".
- `Projects/<repo-slug>/` missing → offer `/obsidian-project` or continue.

### Phase 3 (Q&A loop)
- 3 consecutive `Other` + unclear free-text → Claude proactively steps back to re-frame.
- User says "propose now" at Q1 → jump to Phase 4 with `(low confidence)` label on approaches.
- Lazy grep returns 50+ matches → read top 5 by path order; tell user "N more matches available".
- User contradicts earlier turn → Claude flags inconsistency for clarification.
- Checklist stuck at 5/6 and user is tired → accept 5/6, advance.
- Turn count > ~15 → Claude proactively suggests advancing.

### Phase 4 (propose)
- Phase 3 converged at only 4/6 → approaches labeled `(based on partial context)`.
- All 3 approaches collapse to same direction in matrix → return to Phase 3.
- User picks `None` → return to Phase 3 with "why these fell short" context.

### Phase 5 (section-by-section)
- User edit in late section invalidates earlier section → Claude re-presents the affected section, labeled "(updated based on your Section N change)".
- Self-review finds an unresolvable placeholder → promote to Open Questions (Section 9), do not block.

### Phase 6 (write)
- Target directory missing → `mkdir -p` and notify.
- Same-day same-topic collision → suffix `-v2`, `-v3`.
- `<repo>` is read-only filesystem → abort with fallback option (manual vault-only write).
- Vault `Brainstorms/` directory missing → `mkdir -p`.

### Phase 7 (handoff)
- User picks "writing-plans" before write completed → abort with "spec must be written first".
- `superpowers:writing-plans` skill unavailable → print spec path, let user invoke manually.

## 8. Test Strategy

### Tier 1 — Smoke (required for completion)
Run `/obsidian-brainstorm /Users/leric/Desktop/code/obsidian-second-brain` against this repo itself.
**Expected:** Phase 0-7 all complete; spec written to `docs/superpowers/specs/`; vault note written to `Projects/obsidian-second-brain/Brainstorms/`; cross-links bi-directionally valid.

### Tier 2 — Realistic (strongly recommended)
Run `/obsidian-brainstorm /Users/leric/Desktop/code/ai-eden-service "memory v3"`.
**Expected:** Phase 1 vault scan finds 14 dossiers + ADR-003 + ADR-004; Phase 3 has ≥3 Q&A turns; Phase 4 proposes ≥2 approaches; outputs land in `ai-eden-service/docs/superpowers/specs/` and `Projects/ai-eden-service/Brainstorms/`.

### Tier 3 — Edge case scan
- Empty topic: `/obsidian-brainstorm <repo>` → Phase 2 triggers.
- Non-existent repo: `/obsidian-brainstorm /tmp/nope` → abort.
- Repo with no vault footprint: `/obsidian-brainstorm /some/random/repo` → fallback Q1 fires.

### Acceptance checklist (must pass before merge)
- `commands/obsidian-brainstorm.md` contains no "opening provocations" wording.
- `commands/obsidian-brainstorm.md` references `references/brainstorm-question-templates.md`.
- `references/brainstorm-question-templates.md` contains all 6 categories.
- Phase 1 vault scan actually reads files (not just dialogue).
- Phase 3 first question is multi-choice.
- Phase 4 proposes 2-3 approaches with trade-off matrix.
- Phase 4 marks exactly one `(Recommended)`.
- Spec output contains REQ-NNN / AC-NNN IDs.
- Vault note contains `## For future Claude` preamble.
- Vault note frontmatter contains `ai-first: true`.
- Spec + vault note bi-directionally cross-linked (`related_brainstorm` ↔ `spec_path`).
- `bash scripts/build.sh` produces 4 green adapters.
- `CHANGELOG.md` Unreleased entry present.
- `SKILL.md` and `README.md` descriptions updated.

### AI-first compliance for vault note
Run `/obsidian-health` against the produced vault note. Must pass: frontmatter present, `ai-first: true`, preamble present, ≥1 wikilink, tags non-empty, date matches today, no emoji (unless explicit UI element), no em-dash.

### Out of scope for testing
- No pytest / unit tests introduced.
- No LLM answer-quality scoring.
- No cross-platform adapter behavior diff.

## 9. Acceptance Criteria (Given-When-Then)

### AC-001 — Positional topic argument
- **Given** the user runs `/obsidian-brainstorm /path/to/repo "memory schema v3"`
- **When** Phase 0 parses arguments
- **Then** `<repo>` = `/path/to/repo` and `<topic>` = `memory schema v3`, no Phase 2 triggered.

### AC-002 — Empty topic triggers discovery
- **Given** the user runs `/obsidian-brainstorm /path/to/repo` with no topic
- **When** Phase 1 vault scan completes
- **Then** Phase 2 presents Q1 with ≥4 multi-choice options + `(Other)`, sourced from vault `open_gaps` and `hot_keywords`.

### AC-003 — Multi-select followed by ordering
- **Given** Phase 2 Q1 is presented and user multi-selects 2+ options
- **When** user submits the selection
- **Then** Claude asks a follow-up: "which of these should we drill first?"

### AC-004 — Convergence checklist enforces advance
- **Given** Phase 3 is in progress
- **When** ≥5/6 checklist items are checked
- **Then** Claude proposes advancing to Phase 4 at the next turn boundary.

### AC-005 — Lazy code-fetch only when triggered
- **Given** Phase 3 is starting and no user answer has triggered Case A/B/C
- **When** Claude prepares the next question
- **Then** no files have been read by the skill yet (vault notes from Phase 1 don't count).

### AC-006 — Approach proposal includes blast-radius
- **Given** Phase 4 proposes 3 approaches
- **When** each approach is rendered
- **Then** each includes a "what changes in code" with file paths and approximate LOC, AND a "what stays the same".

### AC-007 — Exactly one Recommended
- **Given** Phase 4 has rendered all approaches
- **When** the recommendation line is presented
- **Then** exactly one approach is marked `(Recommended)` with a justification grounded in a specific Phase 3 answer.

### AC-008 — User dissent loops back
- **Given** Phase 4 has presented approaches
- **When** the user picks `None`
- **Then** the flow returns to Phase 3 with a context note explaining why the 3 approaches were rejected.

### AC-009 — Section-by-section approval
- **Given** Phase 5 is in progress, currently on Section N
- **When** the user replies "OK"
- **Then** Claude advances to Section N+1 and presents it.

### AC-010 — Back-step regenerates downstream
- **Given** Phase 5 is on Section 7 and user requests return to Section 2
- **When** the user modifies Section 2
- **Then** Claude re-presents Section 2 with edits, then walks downstream affected sections labeled "(updated based on your Section 2 change)".

### AC-011 — Self-review fixes placeholders inline
- **Given** the design is complete and self-review runs
- **When** a `TBD` is found
- **Then** Claude either resolves it inline using existing context, or promotes it to Section 9 (Open Questions); the user is not re-prompted.

### AC-012 — Dual output written
- **Given** Phase 6 executes
- **When** both files are written
- **Then** the engineering spec exists at `<repo>/docs/superpowers/specs/<date>-<slug>-design.md` and the vault note exists at `<vault>/Projects/<repo-slug>/Brainstorms/<date>-<slug>.md`.

### AC-013 — Bi-directional cross-link
- **Given** both files exist after Phase 6
- **When** the frontmatter of each is parsed
- **Then** spec contains `related_brainstorm:` pointing to the vault note, AND vault note contains `spec_path:` pointing to the spec.

### AC-014 — Collision suffix
- **Given** a file with the same date and slug already exists in either output target
- **When** Phase 6 writes
- **Then** the new file is suffixed `-v2` (or `-v3`, etc.), and the existing file is untouched.

### AC-015 — Handoff is opt-in
- **Given** Phase 7 is reached
- **When** options are presented
- **Then** the command does NOT auto-invoke `superpowers:writing-plans`; only an explicit user pick triggers it.

## 10. Out of Scope

1. No automated test framework (pytest / jest / etc.) introduced this PR.
2. No changes to other thinking-tool commands (`/obsidian-decide`, `/obsidian-challenge`, `/obsidian-architect`, etc.) — even if the iterative-Q&A pattern is reusable, prove it on brainstorm first.
3. No LLM self-evaluation or quality scoring of brainstorm output.
4. No multi-language detection or auto-switching — follow user's input language.
5. No multi-repo brainstorm in one invocation.
6. No mid-brainstorm state persistence or resume.
7. No auto-chain to `superpowers:writing-plans` — Phase 7 is an offer, not a default.
8. No deep edits to other `commands/*.md` files beyond `SKILL.md` description sync.
9. No migration of v1 session files in `Inbox/` — they remain as-is.

## 11. Open Questions

### OQ-1 — Stepping back from 3 consecutive "Other"
How to prompt-engineer Claude to reliably detect 3 consecutive `(Other)` + unclear free-text and proactively step back? This depends on LLM behavior and cannot be 100% locked in markdown instruction.
**Mitigation:** include an explicit example dialogue in `commands/obsidian-brainstorm.md`.

### OQ-2 — Lazy code-fetch ranking
How should `grep`-returned top-5 files be ranked?
- Default (implementation choice): `ripgrep --sort path` first 5.
- Future improvement: rank by topic-keyword frequency.
**Decision:** ship default; upgrade if dogfooding shows poor ranking.

### OQ-3 — "Key turning-point quote" subjective criterion
Vault note Q&A summary includes both摘要 and verbatim key quotes. The "key" judgment is Claude-subjective.
**Mitigation:** in `commands/obsidian-brainstorm.md` define "key quote = an answer that flipped the approach selection".

### OQ-4 — Section 5 (Interfaces / APIs) for pure-dialogue brainstorms
For brainstorms that don't touch APIs (e.g. process redesign), Section 5 is frequently N/A. Should it be skipped by default?
**Decision:** keep Section 5 in walk order but allow `skip with reason`. Re-evaluate after 3 dogfooding runs.

### OQ-5 — Meta-case (brainstorming this repo about itself)
When the user brainstorms `obsidian-second-brain` itself, the `<repo>` and the skill living-place are the same. Does this cause any cross-link or path collision?
**Decision:** verify in Tier 1 smoke; document any meta-case adjustments in `commands/obsidian-brainstorm.md`.

## 12. Success Criteria

- **SC-1:** Tier 1 smoke against `obsidian-second-brain` itself runs Phase 0-7 cleanly, produces spec + vault note, cross-links valid.
- **SC-2:** Tier 2 realistic run against `ai-eden-service` produces a spec that `superpowers:writing-plans` consumes successfully to produce an implementation plan.
- **SC-3:** Produced vault note passes `/obsidian-health`.
- **SC-4:** User (Eugeniu) self-assessment: "better than v1".
- **SC-5:** All 4 adapters rebuild cleanly (`bash scripts/build.sh`) and the brainstorm description row aligns across `claude-code` / `codex-cli` / `gemini-cli` / `opencode`.

## 13. References

- `commands/obsidian-brainstorm.md` — the v1 command file to be rewritten
- `commands/obsidian-research-deep.md` — parallel positional-arg shape pattern (commit `66791b1` modeled after this)
- `references/ai-first-rules.md` — vault-write spec, non-negotiable for vault note
- `docs/superpowers/specs/2026-05-29-obsidian-brainstorm-design.md` — superseded v1 design
- `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/brainstorming/` — reference flow (one-question-at-a-time, multi-choice preferred, propose 2-3 approaches, section-by-section)
- `superpowers:writing-plans` — downstream consumer of the engineering spec
- `Projects/obsidian-second-brain/Brainstorms/2026-06-01-obsidian-brainstorm-v2.md` — the brainstorm session that produced this spec
