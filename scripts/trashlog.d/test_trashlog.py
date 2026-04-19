"""Unit tests for trashlog.

Run: ~/.config/config-venv/bin/pytest ~/.config/scripts/trashlog.d/
"""
import json
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trashlog as tl


# ── helpers ─────────────────────────────────────────────────────────────────

def _bplist_write(path: Path, attr: str, value) -> None:
    """Write a com.apple.metadata: xattr with a bplist-encoded value."""
    data = plistlib.dumps(value, fmt=plistlib.FMT_BINARY)
    import binascii
    hex_str = binascii.hexlify(data).decode()
    subprocess.run(["xattr", "-wx", attr, hex_str, str(path)], check=True)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Isolated config/log/state in a tmp dir, and a fake 'Trash' dir."""
    cfg = tmp_path / "config"
    logs = cfg / "logs"
    logs.mkdir(parents=True)
    fake_trash = tmp_path / "Trash"
    fake_trash.mkdir()

    monkeypatch.setattr(tl, "CONFIG_DIR", cfg)
    monkeypatch.setattr(tl, "LOG_DIR", logs)
    monkeypatch.setattr(tl, "LOG_PATH", logs / "trash.log")
    monkeypatch.setattr(tl, "STATE_PATH", cfg / "state.json")
    monkeypatch.setattr(tl, "TRASH_DIR", fake_trash)
    return tmp_path


# ── xattr helpers ──────────────────────────────────────────────────────────

def test_xattr_plist_missing_returns_none(tmp_path):
    f = tmp_path / "plain.txt"
    f.write_text("x")
    assert tl._xattr_plist(f, "com.apple.metadata:nonexistent") is None


def test_xattr_plist_reads_bplist_value(tmp_path):
    f = tmp_path / "tagged.txt"
    f.write_text("x")
    _bplist_write(f, "com.apple.metadata:hl_expires", "01776507074")
    assert tl._xattr_plist(f, "com.apple.metadata:hl_expires") == "01776507074"


def test_xattr_plist_handles_where_froms_list(tmp_path):
    f = tmp_path / "downloaded.txt"
    f.write_text("x")
    _bplist_write(f, tl.WHERE_FROM_ATTR, ["https://example.com/foo.txt", "https://example.com/"])
    val = tl._xattr_plist(f, tl.WHERE_FROM_ATTR)
    assert val == ["https://example.com/foo.txt", "https://example.com/"]


# ── _int_from_padded ───────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("01776507074", 1776507074),
    ("0", 0),
    ("00000000000", 0),
    ("99999999999", 99999999999),
    (None, None),
    ("not-a-number", None),
    ("", 0),  # empty string after lstrip('0') of itself, falls through to "0"
])
def test_int_from_padded(raw, expected):
    assert tl._int_from_padded(raw) == expected


# ── _collect_metadata ──────────────────────────────────────────────────────

def test_collect_metadata_plain_file(tmp_path):
    f = tmp_path / "plain.txt"
    f.write_text("hello")
    meta = tl._collect_metadata(f)
    assert meta["name"] == "plain.txt"
    assert meta["size_bytes"] == 5
    assert meta["is_dir"] is False
    assert meta["extension"] == "txt"
    assert meta["had_halflife_mark"] is False
    assert meta["halflife_expiry_epoch"] is None
    assert meta["where_from"] is None
    assert meta["mtime"] is not None


def test_collect_metadata_with_halflife_marks(tmp_path):
    f = tmp_path / "marked.txt"
    f.write_text("x")
    _bplist_write(f, tl.HL_XATTR, "01776507074")
    _bplist_write(f, tl.HL_MARKED_AT, "01776500000")
    meta = tl._collect_metadata(f)
    assert meta["had_halflife_mark"] is True
    assert meta["halflife_expiry_epoch"] == 1776507074
    assert meta["halflife_marked_at_epoch"] == 1776500000


def test_collect_metadata_with_where_from(tmp_path):
    f = tmp_path / "downloaded.pdf"
    f.write_text("x")
    _bplist_write(f, tl.WHERE_FROM_ATTR, ["https://example.com/doc.pdf", "https://example.com/"])
    meta = tl._collect_metadata(f)
    assert meta["where_from"] == "https://example.com/doc.pdf"


def test_collect_metadata_directory(tmp_path):
    d = tmp_path / "a_folder"
    d.mkdir()
    (d / "inside.txt").write_text("x")
    meta = tl._collect_metadata(d)
    assert meta["is_dir"] is True
    assert meta["extension"] is None


def test_collect_metadata_unreadable_path(tmp_path):
    ghost = tmp_path / "does_not_exist.txt"
    meta = tl._collect_metadata(ghost)
    assert meta.get("unreadable") is True


def test_collect_metadata_no_extension(tmp_path):
    f = tmp_path / "README"
    f.write_text("x")
    meta = tl._collect_metadata(f)
    assert meta["extension"] is None


def test_collect_metadata_extension_case_normalized(tmp_path):
    f = tmp_path / "Archive.ZIP"
    f.write_text("x")
    meta = tl._collect_metadata(f)
    assert meta["extension"] == "zip"


# ── _current_inventory ─────────────────────────────────────────────────────

def test_current_inventory_empty_trash(sandbox):
    assert tl._current_inventory() == {}


def test_current_inventory_skips_hidden(sandbox):
    (tl.TRASH_DIR / ".DS_Store").write_text("macos junk")
    (tl.TRASH_DIR / ".localized").write_text("")
    (tl.TRASH_DIR / "real.txt").write_text("x")
    inv = tl._current_inventory()
    assert set(inv.keys()) == {"real.txt"}


def test_current_inventory_captures_ino_and_size(sandbox):
    (tl.TRASH_DIR / "foo.bin").write_bytes(b"x" * 1024)
    inv = tl._current_inventory()
    assert "foo.bin" in inv
    assert inv["foo.bin"]["size"] == 1024
    assert inv["foo.bin"]["ino"] > 0


def test_current_inventory_raises_on_permission_error(sandbox, monkeypatch):
    def boom(self):
        raise PermissionError(1, "Operation not permitted")
    monkeypatch.setattr(Path, "iterdir", boom)
    with pytest.raises(tl.InventoryReadError) as exc:
        tl._current_inventory()
    assert "TCC" in str(exc.value) or "permission" in str(exc.value).lower()


# ── state round-trip ───────────────────────────────────────────────────────

def test_read_state_missing_returns_default(sandbox):
    # STATE_PATH doesn't exist yet
    state = tl._read_state()
    assert state == {"files": {}}


def test_read_state_malformed_json_returns_default(sandbox):
    tl.STATE_PATH.write_text("{ not valid json")
    state = tl._read_state()
    assert state == {"files": {}}


def test_write_state_then_read_round_trip(sandbox):
    original = {"files": {"foo.txt": {"ino": 123, "size": 456}}, "last_scan": "2026-04-18"}
    tl._write_state(original)
    assert tl._read_state() == original


# ── _rotate_log ────────────────────────────────────────────────────────────

def test_rotate_log_no_op_below_threshold(sandbox, monkeypatch):
    monkeypatch.setattr(tl, "LOG_ROTATE_BYTES", 1000)
    tl.LOG_PATH.write_bytes(b"a" * 100)
    tl._rotate_log()
    assert tl.LOG_PATH.exists()
    assert not tl.LOG_PATH.with_suffix(".log.old").exists()


def test_rotate_log_renames_above_threshold(sandbox, monkeypatch):
    monkeypatch.setattr(tl, "LOG_ROTATE_BYTES", 1000)
    tl.LOG_PATH.write_bytes(b"b" * 2000)
    tl._rotate_log()
    assert not tl.LOG_PATH.exists()
    assert tl.LOG_PATH.with_suffix(".log.old").stat().st_size == 2000


def test_rotate_log_overwrites_existing_old(sandbox, monkeypatch):
    monkeypatch.setattr(tl, "LOG_ROTATE_BYTES", 1000)
    tl.LOG_PATH.with_suffix(".log.old").write_bytes(b"old generation")
    tl.LOG_PATH.write_bytes(b"c" * 2000)
    tl._rotate_log()
    assert tl.LOG_PATH.with_suffix(".log.old").stat().st_size == 2000


def test_rotate_log_missing_file_harmless(sandbox):
    tl._rotate_log()  # LOG_PATH doesn't exist; must not raise


# ── _append_log ────────────────────────────────────────────────────────────

def test_append_log_writes_valid_jsonl(sandbox):
    tl._append_log({"event": "trashed", "path": "/x"})
    tl._append_log({"event": "gone", "name": "y"})
    lines = tl.LOG_PATH.read_text().splitlines()
    assert len(lines) == 2
    for line in lines:
        json.loads(line)  # raises if malformed


def test_append_log_handles_unicode(sandbox):
    tl._append_log({"name": "café☕.txt"})
    rec = json.loads(tl.LOG_PATH.read_text().splitlines()[0])
    assert rec["name"] == "café☕.txt"


# ── end-to-end watch() against sandboxed Trash ────────────────────────────

def test_watch_first_run_primes_state(sandbox):
    (tl.TRASH_DIR / "a.txt").write_text("x")
    (tl.TRASH_DIR / "b.pdf").write_text("y")
    from click.testing import CliRunner
    r = CliRunner().invoke(tl.cli, ["watch"])
    assert r.exit_code == 0, r.output
    state = tl._read_state()
    assert set(state["files"].keys()) == {"a.txt", "b.pdf"}
    # First run logs existing files as "trashed" (treats prior as empty)
    lines = [json.loads(l) for l in tl.LOG_PATH.read_text().splitlines()]
    trashed_names = {l["name"] for l in lines if l["event"] == "trashed"}
    assert trashed_names == {"a.txt", "b.pdf"}


def test_watch_detects_new_arrival(sandbox):
    from click.testing import CliRunner
    runner = CliRunner()

    # Prime with one file
    (tl.TRASH_DIR / "old.txt").write_text("x")
    runner.invoke(tl.cli, ["watch"])
    old_line_count = len(tl.LOG_PATH.read_text().splitlines())

    # Add a new file, re-scan
    (tl.TRASH_DIR / "new.txt").write_text("y")
    runner.invoke(tl.cli, ["watch"])
    lines = [json.loads(l) for l in tl.LOG_PATH.read_text().splitlines()]
    new_events = lines[old_line_count:]
    assert len(new_events) == 1
    assert new_events[0]["event"] == "trashed"
    assert new_events[0]["name"] == "new.txt"


def test_watch_detects_purge(sandbox):
    from click.testing import CliRunner
    runner = CliRunner()
    (tl.TRASH_DIR / "transient.txt").write_text("x")
    runner.invoke(tl.cli, ["watch"])
    (tl.TRASH_DIR / "transient.txt").unlink()
    runner.invoke(tl.cli, ["watch"])
    last = json.loads(tl.LOG_PATH.read_text().splitlines()[-1])
    assert last["event"] == "gone"
    assert last["name"] == "transient.txt"


def test_watch_idempotent_no_changes(sandbox):
    from click.testing import CliRunner
    runner = CliRunner()
    (tl.TRASH_DIR / "stable.txt").write_text("x")
    runner.invoke(tl.cli, ["watch"])
    lines_after_first = len(tl.LOG_PATH.read_text().splitlines())
    # Second run with no Trash changes: no new events
    runner.invoke(tl.cli, ["watch"])
    assert len(tl.LOG_PATH.read_text().splitlines()) == lines_after_first


def test_watch_surfaces_tcc_error_without_clobbering_state(sandbox, monkeypatch):
    from click.testing import CliRunner
    runner = CliRunner()
    # Prime state with real contents
    (tl.TRASH_DIR / "precious.txt").write_text("x")
    runner.invoke(tl.cli, ["watch"])
    primed = tl._read_state()
    assert "precious.txt" in primed["files"]

    # Now simulate TCC block
    def boom(self):
        raise PermissionError(1, "Operation not permitted")
    monkeypatch.setattr(Path, "iterdir", boom)
    r = runner.invoke(tl.cli, ["watch"])
    assert r.exit_code == 1, "watch must exit nonzero on TCC failure"

    # State must NOT have been wiped
    after_fail = tl._read_state()
    assert after_fail == primed, "state was clobbered by a failed read!"

    # And the log should record the error
    last = json.loads(tl.LOG_PATH.read_text().splitlines()[-1])
    assert last["event"] == "read_error"


def test_watch_captures_halflife_marks(sandbox):
    from click.testing import CliRunner
    target = tl.TRASH_DIR / "hl_marked.txt"
    target.write_text("x")
    _bplist_write(target, tl.HL_XATTR, "01800000000")
    _bplist_write(target, tl.HL_MARKED_AT, "01776000000")
    runner = CliRunner()
    runner.invoke(tl.cli, ["watch"])
    rec = next(
        json.loads(l) for l in tl.LOG_PATH.read_text().splitlines()
        if json.loads(l).get("name") == "hl_marked.txt"
    )
    assert rec["had_halflife_mark"] is True
    assert rec["halflife_expiry_epoch"] == 1800000000
    assert rec["halflife_marked_at_epoch"] == 1776000000


def test_watch_name_collision_same_name_different_inode(sandbox):
    """Finder renames on collision (foo → foo 2) but we also need to handle
    the corner case where an old file is replaced by a new one with the same
    name — e.g. someone emptied trash and dragged another 'foo.txt' in."""
    from click.testing import CliRunner
    runner = CliRunner()
    f = tl.TRASH_DIR / "same.txt"
    f.write_text("first")
    runner.invoke(tl.cli, ["watch"])
    # Replace with different content → different inode on most filesystems
    old_ino = f.stat().st_ino
    f.unlink()
    f.write_text("second")
    new_ino = f.stat().st_ino
    if old_ino == new_ino:
        pytest.skip("filesystem reused inode; can't distinguish replacement")
    runner.invoke(tl.cli, ["watch"])
    # We should see: one "gone" (for old inode) + one "trashed" (for new inode)
    # …or at least a new "trashed" event for the replacement
    events = [json.loads(l) for l in tl.LOG_PATH.read_text().splitlines()]
    assert sum(1 for e in events if e.get("name") == "same.txt" and e["event"] == "trashed") >= 2


# ── stats command ──────────────────────────────────────────────────────────

def test_stats_empty_log_exits_nonzero(sandbox):
    from click.testing import CliRunner
    r = CliRunner().invoke(tl.cli, ["stats"])
    assert r.exit_code == 1
    assert "no log yet" in r.output.lower()


def test_stats_json_output_is_valid(sandbox):
    from click.testing import CliRunner
    runner = CliRunner()
    (tl.TRASH_DIR / "a.mp4").write_text("x" * 1000)
    (tl.TRASH_DIR / "b.mp4").write_text("y" * 2000)
    (tl.TRASH_DIR / "c.pdf").write_text("z" * 500)
    runner.invoke(tl.cli, ["watch"])
    r = runner.invoke(tl.cli, ["stats", "--json"])
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert data["total_trashed"] == 3
    assert data["total_bytes_trashed"] == 3500
    # ext breakdown
    counts = dict(data["top_extensions_by_count"])
    assert counts.get("mp4") == 2
    assert counts.get("pdf") == 1


def test_stats_since_until_filter(sandbox):
    from click.testing import CliRunner
    runner = CliRunner()
    # Inject a stale event + a recent event manually
    tl._append_log({"event": "trashed", "trashed_at": "2025-01-01T00:00:00+00:00",
                    "name": "old.txt", "size_bytes": 10, "extension": "txt",
                    "had_halflife_mark": False, "age_at_trash_days": 0})
    tl._append_log({"event": "trashed", "trashed_at": "2026-06-01T00:00:00+00:00",
                    "name": "new.txt", "size_bytes": 20, "extension": "txt",
                    "had_halflife_mark": False, "age_at_trash_days": 0})
    r = runner.invoke(tl.cli, ["stats", "--since", "2026-01-01", "--json"])
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert data["total_trashed"] == 1
    assert data["total_bytes_trashed"] == 20


# ── tail command ───────────────────────────────────────────────────────────

def test_tail_respects_count(sandbox):
    from click.testing import CliRunner
    for i in range(10):
        tl._append_log({"event": "trashed", "name": f"f{i}.txt"})
    r = CliRunner().invoke(tl.cli, ["tail", "-n", "3"])
    assert r.exit_code == 0
    assert len(r.output.strip().splitlines()) == 3


def test_tail_filter_by_event(sandbox):
    from click.testing import CliRunner
    for i in range(3):
        tl._append_log({"event": "trashed", "name": f"t{i}"})
    for i in range(3):
        tl._append_log({"event": "gone", "name": f"g{i}"})
    r = CliRunner().invoke(tl.cli, ["tail", "-n", "10", "--event", "gone"])
    assert r.exit_code == 0
    lines = r.output.strip().splitlines()
    assert len(lines) == 3
    for line in lines:
        assert json.loads(line)["event"] == "gone"


# ── version ─────────────────────────────────────────────────────────────────

def test_version_flag():
    from click.testing import CliRunner
    r = CliRunner().invoke(tl.cli, ["--version"])
    assert r.exit_code == 0
    assert tl.__version__ in r.output


# ── safety: never modifies Trash ───────────────────────────────────────────

def test_watch_does_not_modify_trash(sandbox):
    from click.testing import CliRunner
    runner = CliRunner()
    items = {"a.txt": "hello", "b.pdf": "world"}
    for name, content in items.items():
        (tl.TRASH_DIR / name).write_text(content)
    before_names = {p.name for p in tl.TRASH_DIR.iterdir()}
    before_sizes = {p.name: p.stat().st_size for p in tl.TRASH_DIR.iterdir()}
    runner.invoke(tl.cli, ["watch"])
    runner.invoke(tl.cli, ["watch"])
    runner.invoke(tl.cli, ["stats"])
    runner.invoke(tl.cli, ["tail"])
    after_names = {p.name for p in tl.TRASH_DIR.iterdir()}
    after_sizes = {p.name: p.stat().st_size for p in tl.TRASH_DIR.iterdir()}
    assert after_names == before_names
    assert after_sizes == before_sizes
    for name, content in items.items():
        assert (tl.TRASH_DIR / name).read_text() == content
