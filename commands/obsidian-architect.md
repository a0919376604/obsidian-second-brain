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
`--functions=<off|public>` (default off; `public` generates per-function notes
for symbols on the public API surface), `--skip-sections=<csv>` and
`--only-sections=<csv>` for surgical regeneration, `--lang=<en|zh-TW>` to
override the vault default from `_CLAUDE.md`'s `- output-lang:` line.

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

## Phase 3: Per-module synthesis

For each module in the approved manifest where `excluded: false`:

1. Read the lockfile (`Projects/<P>/Architecture/_manifest.lock.json` if it exists)
   and call `decide_module_refresh()` from `scripts/architect/refresh.py` to
   choose generate / regenerate / skip.

2. For generate or regenerate, run repomix to pack the module:

   ```bash
   repomix --include "<module-paths>" --style xml --compress
   ```

   If the packed output exceeds 80,000 tokens as reported by repomix,
   re-pack with `--top-files-len 5` plus include only file headers
   (docstrings or leading comment block) for the rest. Set
   `scan-truncated: true` in the module note frontmatter.

3. Write `Projects/<P>/Architecture/modules/<slug>.md` following the schema
   in `references/ai-first-rules.md` (type: architecture-module).
   Body sections must be wrapped in sentinels:
   - `## What it does` -> `<!-- @generated:start what-it-does -->` block.
     If manifest has `description: <text>`, insert that text verbatim into
     this block (LLM does not regenerate).
   - `## How it works` -> generated block
   - `## Key files` -> generated block
   - `## Depends on` -> generated block (wikilinks to other module notes)
   - `## Consumed by` -> generated block (inverse)
   - `## Recent activity` -> generated block (last 5 git commits via
     `git log -5 --oneline -- <paths>`)
   - `## Related` -> generated block

   For the existing-note case (regenerate), first parse the existing file with
   `scripts/architect/sentinels.parse_blocks()`. Replace `@generated` block
   bodies; preserve `@user` blocks verbatim; for content outside any sentinel,
   compare against lockfile `note_blocks` hash and preserve if user-edited
   (emit a warning).

4. Update the lockfile's `note_blocks` entry for this note with hashes of the
   newly written generated blocks.

After every non-excluded module is processed: continue to Phase 3.5, then
regenerate `overview.md`.

## Phase 3.5: Per-section synthesis

Resolve `output_lang`:

```bash
uv run python -c "from scripts.architect.lang import resolve_output_lang; from pathlib import Path; import sys; print(resolve_output_lang(sys.argv[1] or None, Path(sys.argv[2])))" "${LANG_FLAG:-}" "<vault-root>"
```

For each section in order (`api-surface`, `features`, `decisions`, `roadmap`,
`future`), and for each non-skipped section per `--skip-sections` /
`--only-sections`:

1. Call `scripts.architect.sections.collect_signals(section, scan_report, manifest_modules)` to get the signal subset.
2. Compute `signal_hash(signal)` and call `scripts.architect.refresh.decide_section_refresh(lock, section=..., current_signal=hash, current_lang=output_lang, force=force, refresh_flag=refresh)`. If SKIP, continue.
3. For api-surface, use the deterministic table renderers from `scripts.architect.api_surface_render` — no LLM call for the table contents; LLM only writes the `summary` block.
4. For features / decisions / roadmap / future, build the LLM prompt with `sections.build_prompt(...)`, run it, parse the JSON response into a `{block-name: body}` dict.
5. Call `sections.compose_note(section=..., generated_blocks=..., output_lang=..., ...)` to assemble the markdown.
6. Write to `Projects/<P>/Architecture/<filename>`.
7. Update the lockfile `sections[<name>]` entry with the new `signal-hash`, `lang`, `note-blocks-hash`, and `last-generated` timestamp.

For per-section content rules see `references/ai-first-rules.md` §language and §architecture-*.

If `--functions=public`:

8. Call `scripts.architect.public_surface.eligible_functions(api_surface, module_paths)` to get the candidate list.
9. For each candidate, run an LLM call to produce the body blocks (`what-it-does`, `inputs-and-outputs`, `behavior-notes`, `callers`).
10. Call `sections.compose_function_note(...)` and write to `Projects/<P>/Architecture/functions/<module>/<func>.md`.
11. Update lockfile `functions[<module>/<func>]`.

Failure isolation: if any one section or function synthesis throws, write the note with `status: scan-failed`, record the error in the body, and continue.

## Overview synthesis (Phase 4 — MOC style)

Read every section note's `## Summary` block, plus stack, modules, and entry
points from the scan-report.

Run an LLM call to produce only the @generated blocks (`purpose`, `layer-map`,
`external-deps`, `key-abstractions`). The bilingual headings, Capability MOC,
Structure MOC, and stack body are rendered deterministically by
`sections.compose_overview()`.

Write the result to `Projects/<P>/Architecture/overview.md`. The frontmatter
includes `moc-style: true`, the detected `stack:` block (omitted if empty),
and `lang: <output_lang>`.

`overview.md` body section order (matching `compose_overview`):
1. `## For future Claude` / `## 給未來 Claude`
2. `## Purpose` / `## 用途` (LLM block)
3. `## Stack` / `## 技術棧` (deterministic, mirrors frontmatter)
4. `## Capability MOC` / `## 能力地圖 MOC` (wikilinks to all 4 narrative sections)
5. `## API surface` / `## API 介面` (wikilink to api-surface.md)
6. `## Structure MOC` / `## 結構地圖 MOC` (module wikilinks + entry points)
7. `## Layer map` / `## 分層圖` (LLM Mermaid block)
8. `## External dependencies` / `## 外部相依` (LLM block)
9. `## Key abstractions` / `## 核心抽象` (LLM block)
10. `## Related` / `## 相關`

## Data flow note (optional)

If the scan report identifies at least one entry point with a clear
input -> output chain (a chain reachable from the entry point through
multiple modules), generate `Projects/<P>/Architecture/data-flow.md`
with a Mermaid sequence diagram plus brief walkthrough. Skip if no such
chain is detectable - never write speculative data-flow diagrams.

## Hub note update

Generate the `## Architecture` block via
`scripts.architect.refresh.render_hub_architecture_block(...)`, passing
`lang=output_lang`. Append or replace in `Projects/<P>/<P>.md`.

In `en` mode, the heading is `## Architecture`; in `zh-TW`, `## 架構`.
Idempotent: section exists -> replace in place; otherwise append.

Note: other commands (`/obsidian-project`, `/obsidian-board`) may still
write English headings into the same hub. Mixed-language is tolerated
during the cross-command rollout.

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
