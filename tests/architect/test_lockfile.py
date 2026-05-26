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
