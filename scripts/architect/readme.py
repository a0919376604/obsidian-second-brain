"""Extract recognized sections from a README.

Returns a dict {canonical_section_name: body_text} where canonical names are
title-case strings drawn from a fixed alias map. Unknown sections are ignored.
"""

from __future__ import annotations

import re

# Map of lowercase alias -> canonical title-case name.
_ALIASES = {
    "features": "Features",
    "capabilities": "Features",
    "roadmap": "Roadmap",
    "coming soon": "Coming Soon",
    "upcoming": "Coming Soon",
    "limitations": "Limitations",
    "known issues": "Known Issues",
    "known limitations": "Limitations",
    "future work": "Future Work",
    "future": "Future Work",
    "what's next": "Future Work",
}

_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def extract_sections(text: str) -> dict[str, str]:
    """Return {canonical_name: body} for every recognized H2 in `text`.

    Body is the raw text between this H2 and the next H2 (or EOF), stripped.
    """
    matches = list(_H2_RE.finditer(text))
    if not matches:
        return {}
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        title = m.group(1).strip().lower()
        canonical = _ALIASES.get(title)
        if canonical is None:
            continue
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[canonical] = text[body_start:body_end].strip()
    return out
