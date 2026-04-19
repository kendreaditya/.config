"""Unit tests for halflife.

Run: ~/.config/config-venv/bin/pytest ~/.config/scripts/halflife.d/
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import halflife as hl


# ── parse_duration ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("s,expected", [
    ("30s", 30),
    ("30m", 30 * 60),
    ("2h", 2 * 3600),
    ("7d", 7 * 86400),
    ("2w", 2 * 604800),
    ("1y", 31557600),
    ("+7d", 7 * 86400),
    ("-3d", -3 * 86400),
])
def test_parse_duration_valid(s, expected):
    assert hl.parse_duration(s) == expected


@pytest.mark.parametrize("s", [
    "7days", "1 week", "abc", "", "7", "7x", "1.5d", "1d12h",
])
def test_parse_duration_invalid(s):
    import click
    with pytest.raises(click.BadParameter):
        hl.parse_duration(s)


# ── pad ──────────────────────────────────────────────────────────────────────

def test_pad_width_and_ordering():
    # 11-digit padding means lex order = numeric order for non-negative epochs
    small = hl.pad(1)
    big = hl.pad(1_700_000_000)
    assert len(small) == hl.PAD_WIDTH == len(big)
    assert small < big  # lex < numeric


# ── bplist round-trip ───────────────────────────────────────────────────────

def test_bplist_round_trip():
    for s in ["01776507074", "hello", "", "0"]:
        assert hl._bplist_decode(hl._bplist_encode(s)) == s


# ── xattr round-trip ────────────────────────────────────────────────────────

def test_write_read_round_trip(tmp_path):
    f = tmp_path / "target.txt"
    f.write_text("x")
    hl.write_expiry(str(f), 1713589200)
    assert hl.read_expiry(str(f)) == 1713589200
    # marked_at stamped too
    assert hl.read_marked_at(str(f)) is not None


def test_read_expiry_returns_none_when_unmarked(tmp_path):
    f = tmp_path / "unmarked.txt"
    f.write_text("x")
    assert hl.read_expiry(str(f)) is None


def test_read_expiry_raises_on_corrupt_bplist(tmp_path):
    import subprocess
    f = tmp_path / "corrupt.txt"
    f.write_text("x")
    subprocess.run(
        ["xattr", "-w", hl.XATTR, "not a valid bplist", str(f)],
        check=True,
    )
    with pytest.raises(hl.HLReadError) as exc:
        hl.read_expiry(str(f))
    assert exc.value.kind == "corrupt"


def test_clear_expiry_removes_both_xattrs(tmp_path):
    import subprocess
    f = tmp_path / "target.txt"
    f.write_text("x")
    hl.write_expiry(str(f), 1713589200)
    hl.clear_expiry(str(f))
    # neither xattr should remain
    out = subprocess.run(["xattr", "-l", str(f)], capture_output=True, text=True).stdout
    assert "hl_expires" not in out
    assert "hl_marked_at" not in out


# ── fmt_delta ───────────────────────────────────────────────────────────────

def test_fmt_delta_picks_largest_unit():
    assert hl.fmt_delta(59) == "59s"
    assert hl.fmt_delta(61) == "1m"
    assert hl.fmt_delta(3601) == "1h"
    assert hl.fmt_delta(86401) == "1d"
    assert hl.fmt_delta(-3600) == "-1h"


# ── denylist ────────────────────────────────────────────────────────────────

def test_is_denylisted_exact_and_prefix(tmp_path):
    safe = tmp_path / "safe.txt"; safe.write_text("x")
    blocked_dir = tmp_path / "blocked"; blocked_dir.mkdir()
    blocked_file = blocked_dir / "secret.txt"; blocked_file.write_text("x")
    denylist = [str(blocked_dir)]
    assert hl.is_denylisted(safe, denylist) is False
    assert hl.is_denylisted(blocked_file, denylist) is True
    assert hl.is_denylisted(blocked_dir, denylist) is True  # exact match


def test_is_denylisted_expands_home():
    # ~/.ssh should always be denylisted in the default config
    cfg = hl.load_config()
    ssh = Path.home() / ".ssh"
    if ssh.exists():
        assert hl.is_denylisted(ssh, cfg["denylist"]) is True


# ── parse_iso tz handling ───────────────────────────────────────────────────

def test_parse_iso_local_vs_utc():
    # Naive "2028-01-01" interpreted differently under --utc vs local
    ep_local, tz_local = hl.parse_iso("2028-01-01", utc=False)
    ep_utc, tz_utc = hl.parse_iso("2028-01-01", utc=True)
    # UTC and local diverge by some offset (unless the host runs in UTC)
    assert tz_utc == "UTC"
    # ep_utc is what you'd get if you forced UTC interpretation
    from datetime import datetime, timezone
    expected_utc = int(datetime(2028, 1, 1, tzinfo=timezone.utc).timestamp())
    assert ep_utc == expected_utc


def test_parse_iso_explicit_tz_is_not_overridden_by_utc_flag():
    # If the input already names a tz, --utc must NOT reinterpret it.
    ep_noflag, _ = hl.parse_iso("2028-01-01T12:00:00+09:00", utc=False)
    ep_utcflag, _ = hl.parse_iso("2028-01-01T12:00:00+09:00", utc=True)
    assert ep_noflag == ep_utcflag  # JST-9 offset preserved either way


# ── safe_read_expiry (logging wrapper) ─────────────────────────────────────

def test_safe_read_expiry_returns_none_on_corrupt(tmp_path):
    import subprocess
    f = tmp_path / "corrupt.txt"
    f.write_text("x")
    subprocess.run(["xattr", "-w", hl.XATTR, "garbage", str(f)], check=True)
    # safe_read_expiry swallows HLReadError and returns None; raw read_expiry raises
    assert hl.safe_read_expiry(str(f)) is None
    with pytest.raises(hl.HLReadError):
        hl.read_expiry(str(f))


def test_safe_read_expiry_round_trip(tmp_path):
    f = tmp_path / "good.txt"
    f.write_text("x")
    hl.write_expiry(str(f), 1700000000)
    assert hl.safe_read_expiry(str(f)) == 1700000000


# ── read_marked_at ──────────────────────────────────────────────────────────

def test_read_marked_at_returns_none_when_unmarked(tmp_path):
    f = tmp_path / "unmarked.txt"
    f.write_text("x")
    assert hl.read_marked_at(str(f)) is None


def test_read_marked_at_is_stamped_by_write_expiry(tmp_path):
    import time as _time
    f = tmp_path / "target.txt"
    f.write_text("x")
    before = int(_time.time())
    hl.write_expiry(str(f), 1700000000)
    after = int(_time.time())
    stamp = hl.read_marked_at(str(f))
    assert stamp is not None
    assert before <= stamp <= after


# ── _rotate_log ────────────────────────────────────────────────────────────

def test_rotate_log_no_op_below_threshold(tmp_path):
    log = tmp_path / "x.log"
    log.write_bytes(b"a" * 100)  # way under 1 MiB
    hl._rotate_log(log, max_bytes=1000)
    assert log.exists() and log.stat().st_size == 100
    assert not log.with_suffix(".log.old").exists()


def test_rotate_log_renames_above_threshold(tmp_path):
    log = tmp_path / "x.log"
    log.write_bytes(b"a" * 2000)
    hl._rotate_log(log, max_bytes=1000)
    assert not log.exists()
    old = log.with_suffix(".log.old")
    assert old.exists() and old.stat().st_size == 2000


def test_rotate_log_overwrites_existing_old(tmp_path):
    log = tmp_path / "x.log"
    old = tmp_path / "x.log.old"
    old.write_bytes(b"previous generation")
    log.write_bytes(b"b" * 2000)
    hl._rotate_log(log, max_bytes=1000)
    assert old.exists() and old.stat().st_size == 2000  # replaced


def test_rotate_log_missing_file_is_harmless(tmp_path):
    # no exception on nonexistent paths
    hl._rotate_log(tmp_path / "does_not_exist.log", max_bytes=10)


# ── load_config ────────────────────────────────────────────────────────────

def test_load_config_falls_back_when_missing(monkeypatch, tmp_path):
    # Point CONFIG_PATH at a nonexistent file; load_config should return defaults
    monkeypatch.setattr(hl, "CONFIG_PATH", tmp_path / "missing.toml")
    monkeypatch.setattr(hl, "_CONFIG_CACHE", None)
    cfg = hl.load_config()
    assert "denylist" in cfg
    assert "~/.ssh" in cfg["denylist"]


def test_load_config_falls_back_on_malformed_toml(monkeypatch, tmp_path):
    bad = tmp_path / "config.toml"
    bad.write_text("this = is = not [valid\ntoml at all")
    monkeypatch.setattr(hl, "CONFIG_PATH", bad)
    monkeypatch.setattr(hl, "_CONFIG_CACHE", None)
    cfg = hl.load_config()
    assert "denylist" in cfg  # loaded from DEFAULT_CONFIG_TOML fallback


# ── _walk_files ────────────────────────────────────────────────────────────

def test_walk_files_skips_symlinks_and_dirs(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b")
    (tmp_path / "link").symlink_to(tmp_path / "a.txt")
    result = {p.name for p in hl._walk_files(tmp_path)}
    assert result == {"a.txt", "b.txt"}  # dir "sub" and symlink "link" excluded


# ── fmt_delta edge cases ───────────────────────────────────────────────────

def test_fmt_delta_zero():
    assert hl.fmt_delta(0) == "0s"


def test_fmt_delta_sub_minute_negative():
    assert hl.fmt_delta(-30) == "-30s"


def test_fmt_delta_exact_boundary():
    # 60 seconds should roll up to "1m" not stay at "60s"
    assert hl.fmt_delta(60) == "1m"
    assert hl.fmt_delta(3600) == "1h"
    assert hl.fmt_delta(86400) == "1d"


# ── pad overflow (pin current behavior) ────────────────────────────────────

def test_pad_at_max_width_boundary():
    # 99_999_999_999 is 11 digits, no padding needed
    assert hl.pad(99_999_999_999) == "99999999999"
    assert len(hl.pad(99_999_999_999)) == 11


def test_pad_overflows_past_11_digits():
    # Documented: pad produces >11 digits when epoch exceeds year 5138.
    # This will break Spotlight's lex-ordering assumption — if we ever hit
    # the year 5000, revisit PAD_WIDTH. Pin the current behavior.
    assert hl.pad(100_000_000_000) == "100000000000"  # 12 digits, not truncated


# ── wrap: _is_regenerable_path ──────────────────────────────────────────────

@pytest.mark.parametrize("rel", [
    "node_modules/foo.js",
    "node_modules/sub/dep.js",
    ".venv/bin/python",
    "__pycache__/mod.cpython-312.pyc",
    ".pytest_cache/v/cache/nodeids",
    ".mypy_cache/3.12/foo.json",
    "target/debug/app",
    "build/index.html",
    "dist/bundle.js",
    ".next/server/pages/_app.js",
    ".git/HEAD",
    ".DS_Store",
    "src/foo.pyc",  # regenerable SUFFIX wins even under a real src dir
])
def test_is_regenerable_path_positive(tmp_path, rel):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")
    assert hl._is_regenerable_path(p, tmp_path) is True


@pytest.mark.parametrize("rel", [
    "src/app.py",
    "README.md",
    "data/dataset.csv",
    "docs/intro.md",
    "weights.bin",
])
def test_is_regenerable_path_negative(tmp_path, rel):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")
    assert hl._is_regenerable_path(p, tmp_path) is False


def test_is_regenerable_path_outside_root_returns_false(tmp_path):
    # A path that's not relative to root shouldn't be considered regenerable
    outside = Path("/tmp/node_modules/x")
    assert hl._is_regenerable_path(outside, tmp_path) is False


# ── wrap: _snapshot_files ──────────────────────────────────────────────────

def test_snapshot_files_keys_by_dev_ino(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    snap = hl._snapshot_files(tmp_path)
    st = f.stat()
    assert (st.st_dev, st.st_ino) in snap
    assert snap[(st.st_dev, st.st_ino)] == f


def test_snapshot_files_skips_symlinks_and_dirs(tmp_path):
    (tmp_path / "real.txt").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("y")
    (tmp_path / "link").symlink_to(tmp_path / "real.txt")
    snap = hl._snapshot_files(tmp_path)
    names = {p.name for p in snap.values()}
    assert names == {"real.txt", "nested.txt"}


def test_snapshot_files_rename_preserves_inode(tmp_path):
    f = tmp_path / "before.txt"
    f.write_text("x")
    before_snap = hl._snapshot_files(tmp_path)
    key = next(iter(before_snap.keys()))
    # rename — inode unchanged on APFS
    f.rename(tmp_path / "after.txt")
    after_snap = hl._snapshot_files(tmp_path)
    assert key in after_snap  # same (dev, ino) present
    assert after_snap[key].name == "after.txt"


# ── wrap: end-to-end via CliRunner ─────────────────────────────────────────

@pytest.fixture
def in_tmpdir(tmp_path, monkeypatch):
    """chdir into tmp_path so wrap's default-cwd behavior works."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_wrap_marks_new_files(in_tmpdir):
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli,
        ["wrap", "--in", "7d", "--", "sh", "-c", "touch foo.txt bar.txt"])
    assert r.exit_code == 0
    assert hl.read_expiry(str(in_tmpdir / "foo.txt")) is not None
    assert hl.read_expiry(str(in_tmpdir / "bar.txt")) is not None


def test_wrap_skips_regenerable_by_default(in_tmpdir):
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7d", "--",
        "sh", "-c", "touch real.js && mkdir node_modules && touch node_modules/dep.js",
    ])
    assert r.exit_code == 0
    assert hl.read_expiry(str(in_tmpdir / "real.js")) is not None
    assert hl.read_expiry(str(in_tmpdir / "node_modules" / "dep.js")) is None


def test_wrap_follow_regenerable_marks_them(in_tmpdir):
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7d", "--follow-regenerable", "--",
        "sh", "-c", "mkdir node_modules && touch node_modules/dep.js",
    ])
    assert r.exit_code == 0
    assert hl.read_expiry(str(in_tmpdir / "node_modules" / "dep.js")) is not None


def test_wrap_preserves_failing_command_exit_code(in_tmpdir):
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7d", "--",
        "sh", "-c", "touch created.txt; exit 42",
    ])
    assert r.exit_code == 42
    # File was still created, so it should still be marked
    assert hl.read_expiry(str(in_tmpdir / "created.txt")) is not None


def test_wrap_command_not_found(in_tmpdir):
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7d", "--", "this_command_definitely_does_not_exist_xyz",
    ])
    assert r.exit_code == 127
    assert "command not found" in r.output.lower() or "not found" in r.output.lower()


def test_wrap_no_new_files(in_tmpdir):
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, ["wrap", "--in", "7d", "--", "true"])
    assert r.exit_code == 0
    # Exit was clean but nothing to mark


def test_wrap_watch_alternate_directory(tmp_path, monkeypatch):
    """When --watch is given, cwd is irrelevant."""
    import subprocess  # noqa — forces availability
    target_dir = tmp_path / "watchme"
    target_dir.mkdir()
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7d", "--watch", str(target_dir), "--",
        "sh", "-c", f"touch {target_dir}/captured.txt",
    ])
    assert r.exit_code == 0
    assert hl.read_expiry(str(target_dir / "captured.txt")) is not None
    # File in cwd should NOT be marked since we watched a different dir
    (cwd / "ignored.txt").write_text("x")  # created after wrap ran, moot
    assert hl.read_expiry(str(cwd / "ignored.txt")) is None


def test_wrap_threshold_gate_without_yes(in_tmpdir, monkeypatch):
    # Force a very low threshold so we don't have to actually create 20 files
    monkeypatch.setattr(hl, "_CONFIG_CACHE", {
        "denylist": [],
        "mark": {"max_files_without_confirm": 2,
                 "max_bytes_without_confirm": 10**9},
    })
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7d", "--",
        "sh", "-c", "touch a b c d e",
    ])
    # Files were created but not marked (threshold blocked)
    assert r.exit_code != 0
    assert "re-run with `--yes`" in r.output.lower() or "--yes" in r.output
    # Verify none of the 5 files got marked
    for name in "abcde":
        assert hl.read_expiry(str(in_tmpdir / name)) is None


def test_wrap_threshold_yes_bypasses(in_tmpdir, monkeypatch):
    monkeypatch.setattr(hl, "_CONFIG_CACHE", {
        "denylist": [],
        "mark": {"max_files_without_confirm": 2,
                 "max_bytes_without_confirm": 10**9},
    })
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7d", "--yes", "--",
        "sh", "-c", "touch a b c d e",
    ])
    assert r.exit_code == 0
    for name in "abcde":
        assert hl.read_expiry(str(in_tmpdir / name)) is not None


def test_wrap_quiet_suppresses_summary(in_tmpdir):
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7d", "--quiet", "--", "sh", "-c", "touch q.txt",
    ])
    assert r.exit_code == 0
    assert "wrap: marked" not in r.output


def test_wrap_invalid_duration(in_tmpdir):
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7days", "--", "true",
    ])
    assert r.exit_code != 0
    assert "7days" in r.output or "expected" in r.output.lower()


def test_wrap_invalid_watch_dir(in_tmpdir):
    from click.testing import CliRunner
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--watch", "/nonexistent/nope/xyz", "--", "true",
    ])
    assert r.exit_code != 0
    assert "not a directory" in r.output.lower()


def test_wrap_passes_through_flags_to_command(in_tmpdir):
    """-O and similar command-native flags must not be eaten by click."""
    from click.testing import CliRunner
    # sh -c with flags embedded in the command string — proves flag-looking
    # strings after `--` get through to the subprocess.
    r = CliRunner().invoke(hl.cli, [
        "wrap", "--in", "7d", "--",
        "sh", "-c", "echo flags=$# && touch withflags.txt", "--", "-O", "--some-flag",
    ])
    assert r.exit_code == 0
    assert hl.read_expiry(str(in_tmpdir / "withflags.txt")) is not None
