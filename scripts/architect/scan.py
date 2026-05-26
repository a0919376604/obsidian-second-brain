"""Phase 1 orchestrator: tie walker + repomix + entry_points + deps + proposal
into a single deterministic output.

This is the public surface called by scripts/architect_scan.py CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scripts.architect.deps import detect_external_deps
from scripts.architect.entry_points import detect_entry_points
from scripts.architect.manifest import Manifest
from scripts.architect.proposal import propose_modules_with_heuristics
from scripts.architect.repomix import pack_repo_metadata
from scripts.architect.walker import git_metadata, language_stats, walk_repo

SCANNER_VERSION = "0.1.0"


@dataclass
class ScanResult:
    manifest: Manifest
    scan_report: dict


def run_phase_one(repo_root: Path) -> ScanResult:
    """Run Phase 1 end-to-end. No vault writes; returns in-memory result."""
    repo_root = repo_root.resolve()

    files = walk_repo(repo_root)
    languages = language_stats(repo_root)
    git_meta = git_metadata(repo_root)
    entry_points = detect_entry_points(repo_root)
    external_deps = detect_external_deps(repo_root)
    modules = propose_modules_with_heuristics(repo_root, entry_points=entry_points)
    pack_meta = pack_repo_metadata(repo_root)

    primary_language = languages[0]["lang"] if languages else "unknown"

    manifest = Manifest(
        version=1,
        repo={
            "name": repo_root.name,
            "root": str(repo_root),
            "primary_language": primary_language,
            "languages": languages,
        },
        last_scan={
            "date": date.today().isoformat(),
            "commit": git_meta["commit"][:7] + ("+dirty" if git_meta["dirty"] else ""),
            "dirty": git_meta["dirty"],
            "scanner_version": SCANNER_VERSION,
        },
        modules=modules,
    )

    scan_report = {
        "files": files,
        "languages": languages,
        "entry_points": entry_points,
        "external_deps": external_deps,
        "pack_metadata": pack_meta,
        "git": git_meta,
        "scanner_version": SCANNER_VERSION,
    }

    return ScanResult(manifest=manifest, scan_report=scan_report)
