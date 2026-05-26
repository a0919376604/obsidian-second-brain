---
description: Scan a codebase and generate architecture overview plus module notes into the project hub
category: vault
triggers_en: ["architect", "architecture doc", "scan repo", "document architecture", "codebase overview"]
---

Use the obsidian-second-brain skill. Execute `/obsidian-architect $ARGUMENTS`:

The argument is `<repo-path>` (local path or github URL). Optional flags:
`--project=<P>` (force project hub binding), `--refresh` (explicit refresh),
`--dry-run` (Phase 1 only, no vault writes), `--force` (ignore "no changes" gate).

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

After every non-excluded module is processed: regenerate `overview.md`.

## Overview synthesis

`Projects/<P>/Architecture/overview.md`:

- Read every module note's frontmatter plus its `## What it does` block.
- Read the full file tree, entry points, external deps from
  `/tmp/architect-<hash>/scan-report.json`.
- Write the overview with sections in this order: `## For future Claude`,
  `## Purpose`, `## Layer map` (one Mermaid `graph TD` diagram, or
  `flowchart LR` if more than 8 top-level nodes), `## Modules` (bullet list
  with wikilinks), `## Entry points`, `## External dependencies` (with
  recency markers `(as of YYYY-MM, source-url)`), `## Key abstractions`,
  `## Related`.

All LLM-written sections wrapped in `@generated` sentinels with appropriate names.

## Data flow note (optional)

If the scan report identifies at least one entry point with a clear
input -> output chain (a chain reachable from the entry point through
multiple modules), generate `Projects/<P>/Architecture/data-flow.md`
with a Mermaid sequence diagram plus brief walkthrough. Skip if no such
chain is detectable - never write speculative data-flow diagrams.

## Hub note update

Append or replace the `## Architecture` section in `Projects/<P>/<P>.md`:

```markdown
## Architecture

- Overview: [[Architecture/overview]] (last scanned YYYY-MM-DD @ `<commit>`)
- Modules: N active, M deprecated
- Refresh: `/obsidian-architect <repo-path> --refresh`
```

Idempotent: section exists -> replace in place; otherwise append.

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
