"""v2 → v3 migration helper.

Drops v2 @generated blocks (file-tree noise) and keeps @user blocks (judgment).
Provides plan-then-apply for safety + tar.gz archive as safety net.
"""

from __future__ import annotations

import re
import tarfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# v2 generated block names that v3 supersedes — these get dropped.
V2_GENERATED_BLOCKS_TO_DROP = {
    "what-it-does", "how-it-works", "key-files",
    "depends-on", "consumed-by", "recent-activity",
}

# v3 generated blocks per file type (module-level).
V3_MODULE_BLOCKS = {"scope", "strengths", "weaknesses", "improvements", "dependencies"}

# Sentinel + heading detection.
_GENERATED_RE = re.compile(
    r"(##\s+[^\n]*\n\s*\n?)?"
    r"<!--\s*@generated:start\s+(\S+)\s*-->"
    r".*?"
    r"<!--\s*@generated:end\s+\2\s*-->\n?",
    re.DOTALL,
)
_USER_NAME_RE = re.compile(r"<!--\s*@user:start\s+(\S+)\s*-->")


@dataclass
class MigrationPlan:
    files_to_modify: list[str] = field(default_factory=list)
    # files_to_modify entry -> {"drop": [block_names], "keep": [block_names], "create": [block_names]}
    blocks_per_file: dict[str, dict[str, list[str]]] = field(default_factory=dict)


def plan_v2_to_v3_migration(arch_dir: Path) -> MigrationPlan:
    """Inspect an Architecture/ tree; return what would change without modifying."""
    plan = MigrationPlan()
    if not arch_dir.is_dir():
        return plan
    # Walk Architecture/*.md and Architecture/modules/*.md
    candidates = list(arch_dir.glob("*.md")) + list((arch_dir / "modules").glob("*.md"))
    for f in sorted(candidates):
        rel = str(f.relative_to(arch_dir))
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        drop = []
        for m in _GENERATED_RE.finditer(text):
            block_name = m.group(2)
            if block_name in V2_GENERATED_BLOCKS_TO_DROP:
                drop.append(block_name)
        keep = list(set(_USER_NAME_RE.findall(text)))
        if not drop and not keep:
            continue
        plan.files_to_modify.append(rel)
        # Determine v3 blocks to create per file type.
        if rel.startswith("modules/"):
            create = sorted(V3_MODULE_BLOCKS)
        else:
            # For overview / features / etc. the relevant blocks differ;
            # the command body inserts them. Here we just declare intent.
            create = ["scope", "strengths", "weaknesses", "improvements"]
        plan.blocks_per_file[rel] = {
            "drop": sorted(drop),
            "keep": sorted(keep),
            "create": create,
        }
    return plan


def apply_v2_to_v3_migration(arch_dir: Path, plan: MigrationPlan, dry_run: bool = False) -> None:
    """Drop v2 @generated blocks (and their preceding H2 heading) in place.

    Leaves @user blocks and unrelated content untouched. Caller is responsible
    for backup (call `backup_architecture_dir` first if desired).
    """
    if dry_run:
        return
    for rel in plan.files_to_modify:
        path = arch_dir / rel
        text = path.read_text(encoding="utf-8")
        new_text = _GENERATED_RE.sub(_drop_if_v2, text)
        # Collapse 3+ consecutive blank lines to 2 for tidiness.
        new_text = re.sub(r"\n{3,}", "\n\n", new_text)
        path.write_text(new_text, encoding="utf-8")


def _drop_if_v2(m: re.Match) -> str:
    """Replacement callback for `_GENERATED_RE`. Drops the match if its block
    name is in V2_GENERATED_BLOCKS_TO_DROP, otherwise leaves the original
    text untouched."""
    block_name = m.group(2)
    if block_name in V2_GENERATED_BLOCKS_TO_DROP:
        return ""
    return m.group(0)


def backup_architecture_dir(arch_dir: Path, archive_root: Path | None = None) -> Path:
    """Tar.gz the entire Architecture/ tree to a timestamped path.

    Default archive_root is `<arch_dir>/.._archive/`. Returns the archive path.
    """
    if archive_root is None:
        archive_root = arch_dir.parent / "_archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    archive = archive_root / f"architecture-pre-v3-{ts}.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(arch_dir, arcname=arch_dir.name)
    return archive
