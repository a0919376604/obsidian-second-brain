import tarfile
from pathlib import Path

from scripts.architect.migration import (
    MigrationPlan,
    plan_v2_to_v3_migration,
    apply_v2_to_v3_migration,
    backup_architecture_dir,
)


def _setup_v2_architecture(arch_root: Path):
    """Create a synthetic v2 layout: modules/X.md with @generated blocks."""
    (arch_root / "modules").mkdir(parents=True)
    (arch_root / "modules" / "backend.md").write_text(
        "---\ntype: architecture-module\n---\n\n"
        "## For future Claude\nPreamble.\n\n"
        "## What it does\n"
        "<!-- @generated:start what-it-does -->\n"
        "It does backend things.\n"
        "<!-- @generated:end what-it-does -->\n\n"
        "## Key files\n"
        "<!-- @generated:start key-files -->\n"
        "- backend/main.py\n"
        "- backend/app.py\n"
        "<!-- @generated:end key-files -->\n\n"
        "## User notes\n"
        "<!-- @user:start user-notes -->\n"
        "This module has a tricky lifecycle, see ADR-007.\n"
        "<!-- @user:end user-notes -->\n"
    )


def test_plan_lists_blocks_to_drop_keep_and_archive(tmp_path: Path):
    arch = tmp_path / "Architecture"
    _setup_v2_architecture(arch)
    plan = plan_v2_to_v3_migration(arch)
    assert plan.files_to_modify == ["modules/backend.md"]
    backend_blocks = plan.blocks_per_file["modules/backend.md"]
    # v2 generated blocks slated for removal.
    assert "what-it-does" in backend_blocks["drop"]
    assert "key-files" in backend_blocks["drop"]
    # User block preserved.
    assert "user-notes" in backend_blocks["keep"]


def test_apply_strips_generated_keeps_user_blocks(tmp_path: Path):
    arch = tmp_path / "Architecture"
    _setup_v2_architecture(arch)
    plan = plan_v2_to_v3_migration(arch)
    apply_v2_to_v3_migration(arch, plan, dry_run=False)
    text = (arch / "modules" / "backend.md").read_text()
    # @generated blocks dropped along with their headings.
    assert "@generated:start what-it-does" not in text
    assert "@generated:start key-files" not in text
    assert "It does backend things." not in text
    assert "backend/main.py" not in text
    # @user block kept verbatim.
    assert "@user:start user-notes" in text
    assert "see ADR-007" in text
    # Preamble heading and YAML survive.
    assert "## For future Claude" in text


def test_dry_run_does_not_modify_files(tmp_path: Path):
    arch = tmp_path / "Architecture"
    _setup_v2_architecture(arch)
    before = (arch / "modules" / "backend.md").read_text()
    plan = plan_v2_to_v3_migration(arch)
    apply_v2_to_v3_migration(arch, plan, dry_run=True)
    after = (arch / "modules" / "backend.md").read_text()
    assert before == after


def test_backup_creates_tarball(tmp_path: Path):
    arch = tmp_path / "Architecture"
    _setup_v2_architecture(arch)
    archive = backup_architecture_dir(arch)
    assert archive.exists()
    assert archive.suffix == ".gz"
    # tar.gz contains the architecture tree.
    with tarfile.open(archive, "r:gz") as tf:
        names = tf.getnames()
        assert any("modules/backend.md" in n for n in names)


def test_plan_lists_v3_blocks_to_create(tmp_path: Path):
    arch = tmp_path / "Architecture"
    _setup_v2_architecture(arch)
    plan = plan_v2_to_v3_migration(arch)
    expected_v3 = {"scope", "strengths", "weaknesses", "improvements", "dependencies"}
    actual = set(plan.blocks_per_file["modules/backend.md"]["create"])
    assert expected_v3 <= actual, f"missing v3 blocks: {expected_v3 - actual}"
