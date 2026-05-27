"""Phase 1 orchestrator: tie walker + repomix + entry_points + deps + proposal
plus narrative-signal detectors into a single deterministic output.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from scripts.architect.adr import discover_decision_docs
from scripts.architect.api_surface import detect_api_surface
from scripts.architect.changelog import load_changelog
from scripts.architect.commit_decisions import extract_commit_decisions
from scripts.architect.deps import detect_external_deps
from scripts.architect.entry_points import detect_entry_points
from scripts.architect.manifest import Manifest
from scripts.architect.proposal import propose_modules_with_heuristics
from scripts.architect.readme import extract_sections
from scripts.architect.repomix import pack_repo_metadata
from scripts.architect.stack import detect_stack
from scripts.architect.todos import aggregate_todos
from scripts.architect.walker import git_metadata, language_stats, walk_repo

SCANNER_VERSION = "0.2.0"


@dataclass
class ScanResult:
    manifest: Manifest
    scan_report: dict


def run_phase_one(repo_root: Path) -> ScanResult:
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

    # Narrative signal collection.
    readme_text = (repo_root / "README.md").read_text(encoding="utf-8") if (repo_root / "README.md").exists() else ""
    readme_sections = extract_sections(readme_text)
    changelog = load_changelog(repo_root)
    decision_docs = [asdict(d) for d in discover_decision_docs(repo_root)]
    stack = detect_stack(repo_root)
    module_paths_map = {m["slug"]: m.get("paths", []) for m in modules}
    todos = {
        slug: [asdict(t) for t in items]
        for slug, items in aggregate_todos(repo_root, module_paths_map).items()
    }
    api_surface = detect_api_surface(repo_root)
    commit_decisions = [asdict(c) for c in extract_commit_decisions(repo_root, limit=200)]

    scan_report = {
        "files": files,
        "languages": languages,
        "entry_points": entry_points,
        "external_deps": external_deps,
        "pack_metadata": pack_meta,
        "git": git_meta,
        "scanner_version": SCANNER_VERSION,
        # Narrative additions.
        "readme_sections": readme_sections,
        "changelog": _changelog_to_dict(changelog),
        "decision_docs": decision_docs,
        "stack": stack,
        "todos": todos,
        "api_surface": _api_surface_to_dict(api_surface),
        "commit_decisions": commit_decisions,
    }

    return ScanResult(manifest=manifest, scan_report=scan_report)


def _changelog_to_dict(cl) -> dict:
    if cl is None:
        return {"unreleased": None, "recent_versions": []}
    return {
        "unreleased": cl.unreleased,
        "recent_versions": [asdict(v) for v in cl.recent_versions],
    }


def _api_surface_to_dict(surf) -> dict:
    return {
        "cli_commands": [asdict(c) for c in surf.cli_commands],
        "http_routes": [asdict(r) for r in surf.http_routes],
        "exports": [asdict(e) for e in surf.exports],
        "env_vars": [asdict(v) for v in surf.env_vars],
        "detection_status": surf.detection_status,
    }
