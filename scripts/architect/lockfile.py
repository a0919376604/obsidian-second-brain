"""Lockfile: hash-based tracking of LLM-written content.

For each LLM-written manifest field and note section, we store a SHA-256
hash of the value as written. On refresh, we compute the hash of the
current value; if it matches the lockfile, the field is LLM territory
and may be overwritten. If it does not match, the user edited it and
we preserve.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Lockfile:
    version: int
    scanner_version: str
    fields: dict = field(default_factory=dict)
    note_blocks: dict = field(default_factory=dict)


def hash_value(s: str) -> str:
    """Return 'sha256:<hex>' for stable comparison."""
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_lockfile(path: Path) -> Lockfile | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return Lockfile(
        version=data.get("version", 1),
        scanner_version=data.get("scanner_version", "0.0.0"),
        fields=data.get("fields", {}),
        note_blocks=data.get("note_blocks", {}),
    )


def write_lockfile(lock: Lockfile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(lock), indent=2, sort_keys=True))


def field_was_user_edited(lock: Lockfile, field_key: str, current_value: str) -> bool:
    """True iff the current value differs from the LLM-written value recorded in the lockfile.

    If the field is not in the lockfile (e.g. first-run), returns False
    (treat as LLM-territory; safe because lockfile will be updated on first write).
    """
    record = lock.fields.get(field_key)
    if record is None:
        return False
    return record["hash"] != hash_value(current_value)
