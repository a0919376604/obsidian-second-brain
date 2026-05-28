from pathlib import Path

from scripts.architect.lockfile import Lockfile, field_was_user_edited, hash_value, write_lockfile, load_lockfile


def test_hash_is_stable():
    assert hash_value("hello") == hash_value("hello")
    assert hash_value("hello") != hash_value("world")


def test_field_user_edited_detection(tmp_path: Path):
    lock = Lockfile(version=1, scanner_version="0.1.0", fields={
        "modules.auth.display_name": {"hash": hash_value("Auth"), "value": "Auth"}
    }, note_blocks={})
    # Current manifest still has the LLM-written value: not user-edited.
    assert field_was_user_edited(lock, "modules.auth.display_name", current_value="Auth") is False
    # Current manifest has a different value: user edited it.
    assert field_was_user_edited(lock, "modules.auth.display_name", current_value="Authentication") is True


def test_lockfile_round_trip(tmp_path: Path):
    lock = Lockfile(
        version=1,
        scanner_version="0.1.0",
        fields={"modules.auth.role": {"hash": hash_value("core"), "value": "core"}},
        note_blocks={"modules/auth.md": {"what-it-does": {"hash": hash_value("paragraph")}}},
    )
    target = tmp_path / "_manifest.lock.json"
    write_lockfile(lock, target)
    loaded = load_lockfile(target)
    assert loaded.fields["modules.auth.role"]["value"] == "core"
    assert loaded.note_blocks["modules/auth.md"]["what-it-does"]["hash"] == hash_value("paragraph")


def test_v2_lockfile_round_trip_with_sections(tmp_path: Path):
    from scripts.architect.lockfile import Lockfile, hash_value, load_lockfile, write_lockfile
    lock = Lockfile(
        version=2,
        scanner_version="0.2.0",
        fields={},
        note_blocks={},
        sections={
            "features": {"signal-hash": hash_value("sig"), "lang": "zh-TW",
                         "note-blocks-hash": hash_value("nb"), "last-generated": "2026-05-27T10:00:00Z"},
        },
        functions={
            "cli/main": {"source-hash": hash_value("src"), "last-generated": "2026-05-27T10:00:00Z"},
        },
    )
    target = tmp_path / "_manifest.lock.json"
    write_lockfile(lock, target)
    loaded = load_lockfile(target)
    assert loaded.version == 4
    assert loaded.sections["features"]["lang"] == "zh-TW"
    assert loaded.functions["cli/main"]["source-hash"].startswith("sha256:")


def test_v1_lockfile_migrates_on_load(tmp_path: Path):
    """Loading a v1 lockfile should yield version=4 with empty sections/functions."""
    import json
    from scripts.architect.lockfile import load_lockfile
    target = tmp_path / "_manifest.lock.json"
    target.write_text(json.dumps({
        "version": 1,
        "scanner_version": "0.1.0",
        "fields": {"modules.auth.role": {"hash": "sha256:abc", "value": "core"}},
        "note_blocks": {"modules/auth.md": {"what-it-does": {"hash": "sha256:def"}}},
    }))
    loaded = load_lockfile(target)
    assert loaded.version == 4
    assert loaded.sections == {}
    assert loaded.functions == {}
    # Preserved.
    assert loaded.fields["modules.auth.role"]["value"] == "core"


def test_section_signal_was_changed(tmp_path: Path):
    from scripts.architect.lockfile import Lockfile, hash_value, section_signal_was_changed
    lock = Lockfile(
        version=2,
        scanner_version="0.2.0",
        fields={},
        note_blocks={},
        sections={"roadmap": {"signal-hash": hash_value("X"), "lang": "en",
                              "note-blocks-hash": "", "last-generated": ""}},
        functions={},
    )
    # Signal matches and lang matches: unchanged.
    assert section_signal_was_changed(lock, "roadmap", current_signal="X", current_lang="en") is False
    # Signal differs.
    assert section_signal_was_changed(lock, "roadmap", current_signal="Y", current_lang="en") is True
    # Lang differs (counts as changed).
    assert section_signal_was_changed(lock, "roadmap", current_signal="X", current_lang="zh-TW") is True
    # Missing section: changed (treat as first-run).
    assert section_signal_was_changed(lock, "features", current_signal="anything", current_lang="en") is True


def test_v3_schema_with_frame_marker(tmp_path: Path):
    """v3 adds a `frame` field declaring which architect version produced this lockfile."""
    import json
    from scripts.architect.lockfile import Lockfile, load_lockfile, write_lockfile
    lock = Lockfile(
        version=3,
        scanner_version="0.3.0",
        fields={},
        note_blocks={},
        sections={},
        functions={},
        frame="judgment-v3",
    )
    target = tmp_path / "_manifest.lock.json"
    write_lockfile(lock, target)
    data = json.loads(target.read_text())
    assert data["frame"] == "judgment-v3"
    loaded = load_lockfile(target)
    assert loaded.frame == "judgment-v3"
    assert loaded.version == 4


def test_v2_lockfile_migrates_to_v3_on_load(tmp_path: Path):
    """Loading a v2 lockfile should yield version=4 with frame='description-v2' (legacy marker)."""
    import json
    from scripts.architect.lockfile import load_lockfile, CURRENT_SCHEMA
    target = tmp_path / "_manifest.lock.json"
    target.write_text(json.dumps({
        "version": 2,
        "scanner_version": "0.2.0",
        "fields": {},
        "note_blocks": {},
        "sections": {"features": {"signal-hash": "sha256:abc", "lang": "en"}},
        "functions": {},
    }))
    loaded = load_lockfile(target)
    assert loaded.version == CURRENT_SCHEMA == 4
    # v2 entries preserved; frame defaults to legacy marker.
    assert loaded.sections["features"]["signal-hash"] == "sha256:abc"
    assert loaded.frame == "description-v2"


def test_v4_schema_with_report_frame(tmp_path: Path):
    """v4 lockfile defaults to frame='report-v4'."""
    import json
    from scripts.architect.lockfile import Lockfile, load_lockfile, write_lockfile, CURRENT_SCHEMA
    assert CURRENT_SCHEMA == 4
    lock = Lockfile(
        version=4,
        scanner_version="0.4.0",
        fields={},
        note_blocks={},
        sections={"overview": {"signal-hash": "sha256:abc", "lang": "zh-TW"}},
        functions={},
        frame="report-v4",
    )
    target = tmp_path / "_manifest.lock.json"
    write_lockfile(lock, target)
    loaded = load_lockfile(target)
    assert loaded.version == 4
    assert loaded.frame == "report-v4"


def test_v3_lockfile_migrates_to_v4(tmp_path: Path):
    """Loading a v3 lockfile yields version=4 with frame preserved (judgment-v3)."""
    import json
    from scripts.architect.lockfile import load_lockfile, CURRENT_SCHEMA
    target = tmp_path / "_manifest.lock.json"
    target.write_text(json.dumps({
        "version": 3,
        "scanner_version": "0.3.0",
        "fields": {},
        "note_blocks": {},
        "sections": {"features": {"signal-hash": "x", "lang": "zh-TW"}},
        "functions": {},
        "frame": "judgment-v3",
    }))
    loaded = load_lockfile(target)
    assert loaded.version == CURRENT_SCHEMA == 4
    assert loaded.frame == "judgment-v3"  # preserved until v4 migration runs
    assert loaded.sections["features"]["signal-hash"] == "x"


def test_v2_lockfile_still_migrates_through_to_v4(tmp_path: Path):
    """A pre-v3 vault should still load (frame defaults to description-v2)."""
    import json
    from scripts.architect.lockfile import load_lockfile
    target = tmp_path / "_manifest.lock.json"
    target.write_text(json.dumps({
        "version": 2,
        "scanner_version": "0.2.0",
        "fields": {},
        "note_blocks": {},
        "sections": {},
        "functions": {},
    }))
    loaded = load_lockfile(target)
    assert loaded.version == 4
    assert loaded.frame == "description-v2"
