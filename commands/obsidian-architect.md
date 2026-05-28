---
description: Scan a codebase and generate architecture overview plus module notes into the project hub
argument-hint: <repo>
category: vault
triggers_en: ["architect", "architecture doc", "scan repo", "document architecture", "codebase overview"]
---

Use the obsidian-second-brain skill. Execute `/obsidian-architect $ARGUMENTS`:

The argument is `<repo-path>` (local path or github URL). Optional flags:
`--project=<P>` (force project hub binding), `--refresh` (explicit refresh),
`--dry-run` (Phase 1 only, no vault writes), `--force` (ignore "no changes" gate),
`--functions=<off|public>`, `--skip-sections=<csv>`, `--only-sections=<csv>`,
`--lang=<en|zh-TW>` (override vault `_CLAUDE.md output-lang`).

**v4-specific flags:**
- `--frame=<report|judgment|description>` — default `report` (v4). `judgment`
  falls back to v3 behaviour; `description` to v2. v4 produces 8 files
  (overview + 5 modules + decisions + personas); legacy frames keep their
  larger file counts.
- `--keep-deprecated` — when migrating v3→v4, do NOT delete the 6 obsolete
  files. Not recommended; tar.gz backup already preserves them.
- `--improvements-per-file=<N>` — cap on per-file Imps, default 4. Overview
  cross-cutting Imps cap separately at 5.
- `--require-evidence` — default true. When false, LLM may emit Imps without
  Evidence (debugging only).

If `<repo-path>` is omitted and `pwd` is inside a git repo, default to `.`.
Otherwise ASK the user.

## Project routing

Resolve the target project hub in this order:

1. `--project=<P>` flag.
2. Search the vault for a project hub whose `local-path` frontmatter (resolved
   to an absolute path) equals the absolute path of `<repo-path>`. Exactly one
   match: use it.
3. Zero matches: create a new project hub. Follow the same conventions as
   `/obsidian-project`: sub-folder layout, hub frontmatter schema with `date`,
   `tags: [project]`, `status: active`, `local-path`, the
   `Projects/<P>/{Ideas,Tasks,Decisions,Learnings,Research,Competitors,Recaps}/`
   skeleton, and a `board.md`. Project name defaults to the repo folder basename.
   ASK the user before creating so typos can be corrected.
4. Multiple matches: abort, list candidates, ask user to pass `--project=<P>`.

## Phase 1: Deterministic scan

Run:

```bash
uv run python scripts/architect_scan.py <repo-path> --out /tmp/architect-<hash>/
```

This produces `/tmp/architect-<hash>/_manifest.yml` and `scan-report.json`.

The scan-report includes manifest signals AND narrative signals:
`readme_sections`, `changelog`, `decision_docs`, `stack`, `todos`, `api_surface`,
`commit_decisions`. Phase 3.5 consumes these.

If `--dry-run`, print the manifest to the user and stop. No vault writes.

## Phase 1.5: v2 → v3 migration (only when `--frame=judgment` AND existing vault is v2)

Detect if `Projects/<P>/Architecture/_manifest.lock.json` exists and reports
`schema-version: 2` (or `version` < 3, or `frame != "judgment-v3"`). If so:

1. Call `scripts.architect.migration.plan_v2_to_v3_migration(arch_dir)` to
   compute what would change.
2. Print the plan to the user — list which files will be modified, which
   `@generated` blocks will be dropped (the v2 file-tree noise), and which
   `@user` blocks will be preserved.
3. ASK user: `proceed | dry-run | abort`. (`--force` bypasses with proceed.)
4. On `proceed`: call `scripts.architect.migration.backup_architecture_dir(arch_dir)`
   to write `_archive/architecture-pre-v3-<timestamp>.tar.gz`, then call
   `apply_v2_to_v3_migration(arch_dir, plan, dry_run=False)`.
5. On `dry-run`: call `apply_v2_to_v3_migration(arch_dir, plan, dry_run=True)`
   and stop. User reviews, re-runs without dry-run when ready.

After successful migration, lockfile is overwritten in Phase 5 (per-section
synthesis) with `schema-version: 3` and `frame: "judgment-v3"`.

## Phase 1.6: v3 → v4 migration (only when `--frame=report` AND existing vault is v3)

Detect if `Projects/<P>/Architecture/_manifest.lock.json` exists and reports
`frame: "judgment-v3"` (or `version: 3`).

1. Call `scripts.architect.migration.plan_v3_to_v4_migration(arch_dir)`.
2. Print the plan to the user — 6 files to delete (`future.md`, `roadmap.md`,
   `jobs.md`, `api-surface.md`, `features.md`, `flows.md`), known-limitations
   content to migrate into `decisions.md`, files kept (`overview.md`,
   `modules/*`, `decisions.md`, `personas.md`).
3. ASK user `proceed | dry-run | abort`. `--force` bypasses with proceed.
   `--keep-deprecated` skips the delete step but still merges known-limitations.
4. On `proceed`: call `backup_architecture_dir(arch_dir)` first
   (tar.gz to `_archive/architecture-pre-v4-<timestamp>.tar.gz`), then
   `apply_v3_to_v4_migration(arch_dir, plan, dry_run=False)`.
5. On `dry-run`: call `apply_v3_to_v4_migration(... dry_run=True)` and stop.

After successful migration the overview.md content from v3 is now stale (it's
still the v3 MOC). Phase 4 (Overview synthesis below) overwrites it with v4
report content. Lockfile is rewritten in Phase 5 with `version: 4`,
`frame: "report-v4"`.

## Phase 2: Manifest review

Read `_manifest.yml` from the temp output. If
`Projects/<P>/Architecture/_manifest.yml` already exists in the vault:
diff via `scripts/architect/manifest_diff.py` and show added / removed /
renamed modules to the user. Otherwise show the full proposal.

ASK the user to confirm or edit. They can:

- Approve as proposed.
- Provide an edited YAML (paste it back inline).
- Reject and abort.

On approve: write `Projects/<P>/Architecture/_manifest.yml` to the vault.

## Phase 3: Per-module synthesis (v3 judgment frame)

For each module slug in the approved manifest (not excluded):

1. Pack the module's source paths via repomix:
   ```bash
   repomix --include "<paths>" --style xml --compress > /tmp/architect-<hash>/repomix-<slug>.xml
   ```
2. Build the LLM prompt:
   ```python
   from scripts.architect.sections import build_module_prompt
   prompt = build_module_prompt(
       module_slug=slug,
       repomix_packed=open("/tmp/architect-<hash>/repomix-<slug>.xml").read(),
       agents_md_excerpt=agents_md_text[:5000],
       output_lang=output_lang,
   )
   ```
3. Invoke the LLM. Expect strict JSON with 5 keys:
   `scope, strengths, weaknesses, improvements, dependencies`.
4. Validate the `improvements` block: parse via
   `scripts.architect.sections.parse_improvements_block(...)` and confirm
   ≥1 Imp survives (every Imp must include Why/Evidence/Effort/Risk/Confidence).
   If 0 Imps parse, retry once with stricter prompt; if still 0, write the
   block as `_(無 Evidence-grounded improvements;owner 校對)_` and continue.
5. Compose the module note via `scripts.architect.sections.compose_note(...)`
   with `section="module"` (note: v3 introduces this section name).
6. Write to `Projects/<P>/Architecture/modules/<slug>.md`.
7. Update `_manifest.lock.json` `modules[<slug>]` entry.

The new module note:
- Has NO `## Key files` section.
- Body is judgment, not transcription.
- Dependencies section uses wikilinks only.

## Phase 3.5: Per-section synthesis (v4)

Resolve `output_lang`:

```bash
uv run python -c "from scripts.architect.lang import resolve_output_lang; from pathlib import Path; import sys; print(resolve_output_lang(sys.argv[1] or None, Path(sys.argv[2])))" "${LANG_FLAG:-}" "<vault-root>"
```

Order:
1. **decisions.md** — `compose_note(section="decisions", ...)`. New block
   `known-limitations` is populated from migration carry-over (if any) plus
   LLM additions; the LLM should produce the other blocks (summary,
   stack-rationale, etc.) per existing v3 behavior.
2. **personas.md** — `compose_note(section="personas", ...)`. Lighter v4
   version: drop the heavy pain-points list (those moved to module Imps).

Removed in v4 (no longer written): api-surface.md, features.md, roadmap.md,
future.md, jobs.md, flows.md. If `--frame=judgment` is passed, the v3
behavior is restored and these are written.

api-surface detection still runs as part of Phase 1 deterministic scan; the
data lives in `scan-report.json` for `/obsidian-roadmap` and other tooling.

For per-section content rules see `references/ai-first-rules.md` §language and §architecture-*.

If `--functions=public`:

8. Call `scripts.architect.public_surface.eligible_functions(api_surface, module_paths)` to get the candidate list.
9. For each candidate, run an LLM call to produce the body blocks (`what-it-does`, `inputs-and-outputs`, `behavior-notes`, `callers`).
10. Call `sections.compose_function_note(...)` and write to `Projects/<P>/Architecture/functions/<module>/<func>.md`.
11. Update lockfile `functions[<module>/<func>]`.

Failure isolation: if any one section or function synthesis throws, write the note with `status: scan-failed`, record the error in the body, and continue.

## Phase 4: Overview synthesis (v4 top-down report)

This is the centerpiece of v4. The overview becomes a self-contained report.

1. Gather context inputs:
   - `modules_summary` — slug + display name + 1-line role per module
     (from manifest + module note `## 模組職責` blocks).
   - `personas_summary` — first 2 KB of `personas.md`.
   - `per_module_improvements_summary` — concatenation of each module's
     `## 改進機會` block (capped). The LLM uses this to write cross-cutting
     Imps with proper Evidence wikilinks.
   - `readme_excerpt`, `agents_md_excerpt` — first 4 KB of each.

2. Build the prompt: `scripts.architect.sections.build_overview_prompt(...)`.

3. Invoke the LLM. Expect strict JSON:
   ```json
   {
     "purpose": "...",
     "system-diagram": "```mermaid\\n...\\n```",
     "capabilities": "### Area\\n- ...",
     "flows": "### Flow 1: ...\\n```mermaid\\n...\\n```\\n**摩擦:**\\n- ...",
     "cross-cutting-improvements": "### Imp 1: ...\\n- **為什麼:** ..."
   }
   ```

4. Validate `cross-cutting-improvements` via `parse_improvements_block(...)`.
   Each Imp must cite ≥ 2 modules in its Evidence (cross-cutting requirement).
   If a candidate Imp cites only one module, downgrade it / drop it. Aim for
   3-5 Imps total.

5. Compose: `scripts.architect.sections.compose_overview(...)` assembles the
   8-section report. Stack section is auto-generated from `stack` arg
   (which was detected by Phase 1 scanner). Module map and Drill-down
   sections are deterministic from `modules` arg.

6. Write to `Projects/<P>/Architecture/overview.md`. The frontmatter has
   `report-style: true` and `lang: <output_lang>`.

7. Update lockfile section entry: `sections.overview.signal-hash`,
   `sections.overview.lang`, etc.

## Data flow note (optional)

If the scan report identifies at least one entry point with a clear
input -> output chain (a chain reachable from the entry point through
multiple modules), generate `Projects/<P>/Architecture/data-flow.md`
with a Mermaid sequence diagram plus brief walkthrough. Skip if no such
chain is detectable - never write speculative data-flow diagrams.

## Hub note update (v4)

Append/replace `## Architecture` (or `## 架構` if zh-TW) block in
`Projects/<P>/<P>.md`. v4 wikilinks:

```markdown
## 架構

- 總覽 (top-down 報告): [[Architecture/overview]] (v4 report-style, 上次掃描 YYYY-MM-DD @ `<sha>`)
- 模組設計判斷: [[Architecture/modules/backend]] | [[Architecture/modules/frontend]] | ... (list each module)
- 技術決定 + ADR 候選 + 已知限制: [[Architecture/decisions]]
- 使用者型態 reference: [[Architecture/personas]]
- Curated Roadmap: [[Roadmap]]
- 重新整理: `/obsidian-architect <repo-path> --refresh`
```

The legacy v3 wikilinks to `future.md` / `roadmap.md` / `jobs.md` /
`api-surface.md` / `features.md` / `flows.md` MUST be removed from the
hub block — those vault files no longer exist post-migration.

## Daily and operation log

- If `Logs/` exists: append `**HH:MM** - architect | <P> - N modules (M new, K updated, L deprecated)` to `Logs/YYYY-MM-DD.md`.
- Otherwise append `## [YYYY-MM-DD] architect | <P> - N modules ...` to `log.md`.
- Append to today's daily note `## Activity` section: `- /obsidian-architect: scanned [[<P>]] @ commit <commit>`.

## Errors and edge cases

- Repo path missing / not a git repo: abort with clear error. No vault writes.
- `repomix` not installed: the Python wrapper falls back automatically. Inform the user that runs are slower.
- Vault has no `_CLAUDE.md`: abort, suggest `/obsidian-init`.
- Multiple project hubs match the same `local-path`: abort, list candidates, ask user to disambiguate with `--project=<P>`.
- Dirty working tree: warn, do not block. The manifest records `dirty: true`
  and the commit field is tagged `+dirty`.
- Working tree dirty during refresh: per-module diff uses committed states only,
  so uncommitted module changes do not trigger re-synthesis. User can pass
  `--force` to override.
- A single module's synthesis fails: write the note with `status: scan-failed`
  in frontmatter plus the error message, continue with other modules.

---

**AI-first rule:** Every note created or updated by this command MUST follow `references/ai-first-rules.md` - `## For future Claude` preamble, rich frontmatter (`type`, `date`, `tags`, `ai-first: true`, plus type-specific fields), recency markers per external claim, mandatory `[[wikilinks]]` for every person/project/concept referenced, sources preserved verbatim with URLs inline, and confidence levels where applicable. The vault is for future-Claude retrieval - not human reading.

**Language:** Respect `_CLAUDE.md`'s `- output-lang: zh-TW` line by default; honor `--lang=` flag as a single-run override. Run `scripts.architect.lang.resolve_output_lang(cli_flag, vault_root)` to get the effective language. All narrative section notes, the overview MOC, modules, and the hub `## Architecture` block must use that language. Code identifiers (paths, function names, CLI commands, URLs) and frontmatter keys/enums/sentinels remain English regardless. See `references/ai-first-rules.md` for the full rule set.
