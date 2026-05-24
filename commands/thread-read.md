---
description: Read a single HN or Reddit thread, summarize OP + top arguments
category: research
triggers_en: ["read thread", "summarize this thread", "what's in this discussion"]
---

Use the obsidian-second-brain skill. Execute `/thread-read $ARGUMENTS`:

1. Read `_CLAUDE.md`.

2. Run fetcher:

   ```bash
   uv run -m scripts.research.thread_read "<url>"
   ```

3. Parse JSON. Shape: `{"url": "...", "host": "hackernews|reddit", "data": <raw>}`.

4. Write `Research/Threads/YYYY-MM-DD-<slug>.md` with:
   - `## For future Claude` preamble (note the source URL prominently)
   - `## OP Summary` - TL;DR of the OP
   - `## Top Arguments` - 3-5 grouped by stance, each with verbatim quote + commenter handle
   - `## Notable Counter-takes` - minority views worth knowing
   - `## Sources` - original URL + each cited comment permalink

   Frontmatter `type: thread`.

5. Append log + update index.

---

**AI-first rule:** Every note must follow `references/ai-first-rules.md`.
