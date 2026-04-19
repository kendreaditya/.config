#!/usr/bin/env python3
"""
trashlog — observational logger for ~/.Trash arrivals.

A launchd WatchPaths agent fires `trashlog watch` whenever ~/.Trash changes.
We diff against the last known inventory, extract metadata (size, ctime, mtime,
download origin, halflife mark state), and append JSONL events to
~/.config/trashlog/logs/trash.log.

This tool is strictly observational — it never modifies the trash, never
recommends actions, never interacts with halflife's sweep. It collects data;
`trashlog stats` summarizes it.
"""
import os
import sys

_VENV = os.path.expanduser("~/.config/config-venv")
if os.path.exists(f"{_VENV}/bin/python3") and not sys.prefix.startswith(_VENV):
    os.execv(f"{_VENV}/bin/python3", [f"{_VENV}/bin/python3"] + sys.argv)

import json
import plistlib
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import click
from osxmetadata import OSXMetaData


__version__ = "1.0.0"

LABEL = "com.kendreaditya.trashlog"
TRASH_DIR = Path.home() / ".Trash"
CONFIG_DIR = Path.home() / ".config" / "trashlog"
LOG_DIR = CONFIG_DIR / "logs"
LOG_PATH = LOG_DIR / "trash.log"
STATE_PATH = CONFIG_DIR / "state.json"
PLIST_DST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_ROTATE_BYTES = 10 << 20  # 10 MiB

HL_XATTR = "com.apple.metadata:hl_expires"
HL_MARKED_AT = "com.apple.metadata:hl_marked_at"
WHERE_FROM_ATTR = "com.apple.metadata:kMDItemWhereFroms"


# ── helpers ──────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _read_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {"files": {}}


def _write_state(state: dict) -> None:
    _ensure_dirs()
    STATE_PATH.write_text(json.dumps(state))


def _rotate_log() -> None:
    try:
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > LOG_ROTATE_BYTES:
            LOG_PATH.replace(LOG_PATH.with_suffix(".log.old"))
    except OSError:
        pass


def _append_log(record: dict) -> None:
    _ensure_dirs()
    _rotate_log()
    try:
        with LOG_PATH.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def _xattr_plist(path: Path, attr: str):
    """Read a com.apple.metadata: xattr, decode as bplist. Returns None if missing."""
    try:
        return OSXMetaData(str(path)).get_xattr(
            attr, decode=lambda b: plistlib.loads(b)
        )
    except (KeyError, OSError):
        return None
    except Exception:
        return None


def _int_from_padded(raw) -> int | None:
    if raw is None:
        return None
    try:
        return int(str(raw).lstrip("0") or "0")
    except ValueError:
        return None


def _collect_metadata(path: Path) -> dict:
    """Extract everything interesting from a single trashed path."""
    try:
        st = path.stat()
    except OSError:
        return {"name": path.name, "unreadable": True}

    birth = getattr(st, "st_birthtime", None)
    where_from_val = _xattr_plist(path, WHERE_FROM_ATTR)
    where_from = None
    if isinstance(where_from_val, list) and where_from_val:
        where_from = where_from_val[0]
    elif isinstance(where_from_val, str):
        where_from = where_from_val

    hl_expires = _int_from_padded(_xattr_plist(path, HL_XATTR))
    hl_marked_at = _int_from_padded(_xattr_plist(path, HL_MARKED_AT))

    return {
        "name": path.name,
        "size_bytes": st.st_size,
        "is_dir": path.is_dir(),
        "ctime": datetime.fromtimestamp(birth, timezone.utc).isoformat(timespec="seconds")
                 if birth else None,
        "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
        "extension": path.suffix.lstrip(".").lower() or None,
        "had_halflife_mark": hl_expires is not None,
        "halflife_expiry_epoch": hl_expires,
        "halflife_marked_at_epoch": hl_marked_at,
        "where_from": where_from,
    }


class InventoryReadError(Exception):
    """Surfaced when we can't read the Trash dir at all (usually TCC)."""


def _current_inventory() -> dict:
    """Snapshot ~/.Trash top-level contents as {name: {ino, size}}.

    Raises InventoryReadError if the directory itself is unreadable. This
    usually means macOS TCC is blocking us — under launchd, the process
    needs Full Disk Access granted to the python binary running the script.
    """
    inventory = {}
    try:
        entries = list(TRASH_DIR.iterdir())
    except PermissionError as e:
        raise InventoryReadError(
            f"cannot read {TRASH_DIR}: {e}. macOS TCC likely blocked this "
            f"process. Grant Full Disk Access to "
            f"{Path(sys.executable).resolve()} in "
            f"System Settings → Privacy & Security → Full Disk Access."
        )
    except OSError as e:
        raise InventoryReadError(f"cannot read {TRASH_DIR}: {e}")
    for p in entries:
        if p.name.startswith("."):
            continue  # skip .DS_Store, .localized
        try:
            st = p.stat()
            inventory[p.name] = {"ino": st.st_ino, "size": st.st_size}
        except OSError:
            continue
    return inventory


# ── CLI ──────────────────────────────────────────────────────────────────────

@click.group()
@click.version_option(__version__, prog_name="trashlog")
def cli():
    """Observational logger for ~/.Trash arrivals."""


@cli.command()
def watch():
    """Diff against last scan; log new arrivals and purges."""
    _ensure_dirs()
    state = _read_state()
    prior = state.get("files", {})
    try:
        current = _current_inventory()
    except InventoryReadError as e:
        # Loud and safe: don't clobber state with a bogus read.
        click.echo(f"trashlog watch: {e}", err=True)
        _append_log({
            "event": "read_error",
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "error": str(e),
        })
        sys.exit(1)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # New arrivals: in current but not in prior, OR inode changed (rare)
    for name, info in current.items():
        prior_info = prior.get(name)
        if prior_info and prior_info.get("ino") == info["ino"]:
            continue
        path = TRASH_DIR / name
        meta = _collect_metadata(path)
        record = {"event": "trashed", "trashed_at": now, **meta}
        if meta.get("ctime"):
            try:
                age = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(meta["ctime"])).days
                record["age_at_trash_days"] = age
            except ValueError:
                pass
        _append_log(record)

    # Purges: in prior but not in current (either emptied or Put Back)
    for name, prior_info in prior.items():
        if name not in current:
            _append_log({
                "event": "gone",
                "gone_at": now,
                "name": name,
                "prior_size_bytes": prior_info.get("size"),
                # Note: we can't distinguish Put Back from Empty Trash here.
            })

    state["files"] = current
    state["last_scan"] = now
    _write_state(state)


@cli.command()
@click.option("-n", "count", default=20, help="Last N entries (default 20)")
@click.option("--event", type=click.Choice(["trashed", "gone"]),
              help="Filter to a specific event type")
def tail(count, event):
    """Show recent trash-log entries."""
    if not LOG_PATH.exists():
        click.echo("(no log yet — has `trashlog daemon install` been run?)", err=True)
        sys.exit(1)
    lines = LOG_PATH.read_text().splitlines()
    if event:
        lines = [l for l in lines if f'"event": "{event}"' in l]
    for line in lines[-count:]:
        click.echo(line)


@cli.command()
@click.option("--since", default=None, metavar="ISODATE",
              help="Events at or after this date (e.g. 2026-04-18)")
@click.option("--until", default=None, metavar="ISODATE",
              help="Events strictly before this date")
@click.option("--json", "as_json", is_flag=True,
              help="Emit summary as a single JSON object")
def stats(since, until, as_json):
    """Summarize the trash log."""
    if not LOG_PATH.exists():
        click.echo("(no log yet — has `trashlog daemon install` been run?)", err=True)
        sys.exit(1)

    def _parse(s):
        if not s:
            return None
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    since_dt = _parse(since)
    until_dt = _parse(until)

    trashed, gone = [], []
    with LOG_PATH.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = r.get("trashed_at") or r.get("gone_at")
            if not ts:
                continue
            try:
                t = datetime.fromisoformat(ts)
            except ValueError:
                continue
            if since_dt and t < since_dt:
                continue
            if until_dt and t >= until_dt:
                continue
            (trashed if r.get("event") == "trashed" else gone).append(r)

    total_bytes = sum(e.get("size_bytes", 0) or 0 for e in trashed)
    hl_count = sum(1 for e in trashed if e.get("had_halflife_mark"))
    ages = sorted(e["age_at_trash_days"] for e in trashed
                  if e.get("age_at_trash_days") is not None)
    median_age = ages[len(ages) // 2] if ages else None

    ext_counter = Counter(e.get("extension") or "(none)" for e in trashed)
    ext_bytes = defaultdict(int)
    for e in trashed:
        ext_bytes[e.get("extension") or "(none)"] += (e.get("size_bytes") or 0)

    from_counter = Counter()
    for e in trashed:
        wf = e.get("where_from") or ""
        # coalesce URLs to their host for grouping
        if wf.startswith(("http://", "https://")):
            host = wf.split("/", 3)[2] if wf.count("/") >= 2 else wf
            from_counter[host] += 1

    summary = {
        "range_since": since or "(all time)",
        "range_until": until or "(now)",
        "total_trashed": len(trashed),
        "total_gone": len(gone),
        "total_bytes_trashed": total_bytes,
        "total_gib_trashed": round(total_bytes / (1 << 30), 3),
        "halflife_hit_rate_pct": round(100 * hl_count / len(trashed), 1)
                                  if trashed else 0.0,
        "median_age_at_trash_days": median_age,
        "top_extensions_by_count": ext_counter.most_common(10),
        "top_extensions_by_bytes": sorted(
            ((k, v) for k, v in ext_bytes.items()),
            key=lambda x: -x[1],
        )[:10],
        "top_download_sources": from_counter.most_common(10),
    }

    if as_json:
        click.echo(json.dumps(summary, indent=2))
        return

    click.echo(f"Window: {summary['range_since']} → {summary['range_until']}")
    click.echo(f"Trashed: {summary['total_trashed']} items, "
               f"{summary['total_gib_trashed']:.3f} GiB")
    click.echo(f"Gone:    {summary['total_gone']} (purged from Trash / Put Back)")
    click.echo(f"Halflife marks on trashed files: {summary['halflife_hit_rate_pct']}%")
    if median_age is not None:
        click.echo(f"Median age at trash: {median_age} days")
    click.echo()
    click.echo("Top extensions by count:")
    for ext, n in summary["top_extensions_by_count"]:
        click.echo(f"  {n:>5}  .{ext}")
    click.echo()
    click.echo("Top extensions by bytes:")
    for ext, b in summary["top_extensions_by_bytes"]:
        click.echo(f"  {b / (1 << 20):>9.1f} MiB  .{ext}")
    if summary["top_download_sources"]:
        click.echo()
        click.echo("Top download origins:")
        for host, n in summary["top_download_sources"]:
            click.echo(f"  {n:>5}  {host}")


# ── daemon management ──────────────────────────────────────────────────────

def _executable_path() -> str:
    return shutil.which("trashlog") or str(Path(__file__).resolve())


def _plist_dict() -> dict:
    return {
        "Label": LABEL,
        "ProgramArguments": [_executable_path(), "watch"],
        "WatchPaths": [str(TRASH_DIR)],
        "ThrottleInterval": 5,  # min seconds between fires
        "RunAtLoad": True,       # prime state on install
        "StandardOutPath": str(LOG_DIR / "daemon.out"),
        "StandardErrorPath": str(LOG_DIR / "daemon.err"),
    }


@cli.group()
def daemon():
    """Manage the launchd WatchPaths agent."""


@daemon.command("install")
def daemon_install():
    _ensure_dirs()
    # Preflight: can *this* process read ~/.Trash? If so, Terminal/iTerm has
    # FDA. But launchd runs under a different TCC identity (the python binary
    # itself), so the daemon may still be blocked even when install succeeds.
    # Warn loudly either way.
    try:
        list(TRASH_DIR.iterdir())
    except PermissionError:
        click.echo(
            "WARNING: this process cannot read ~/.Trash. That usually means "
            "Terminal doesn't have Full Disk Access. Install will proceed but "
            "the daemon will fail too — grant FDA first.",
            err=True,
        )

    PLIST_DST.parent.mkdir(parents=True, exist_ok=True)
    with open(PLIST_DST, "wb") as f:
        plistlib.dump(_plist_dict(), f)
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST_DST)],
                   check=False, stderr=subprocess.DEVNULL)
    r = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(PLIST_DST)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        click.echo(f"bootstrap failed: {r.stderr.strip()}", err=True)
        sys.exit(1)

    py_bin = str(Path(sys.executable).resolve())
    click.echo(f"installed: {PLIST_DST}\n"
               f"  watches: {TRASH_DIR}\n"
               f"  log:     {LOG_PATH}\n\n"
               f"IMPORTANT — macOS TCC: launchd runs the python binary under a\n"
               f"different permission identity than your shell. You MUST grant\n"
               f"Full Disk Access to this binary or the daemon cannot read\n"
               f"~/.Trash:\n\n"
               f"  Path to grant:  {py_bin}\n\n"
               f"  1. Open System Settings → Privacy & Security → Full Disk Access\n"
               f"  2. Click + and select the path above\n"
               f"  3. Toggle it on (it may ask for your admin password)\n"
               f"  4. Run: trashlog daemon test\n\n"
               f"Verify later with: `trashlog daemon test` or\n"
               f"`cat {LOG_DIR / 'daemon.err'}` after a trash event.")


@daemon.command("test")
def daemon_test():
    """Check whether this process can read ~/.Trash (TCC preflight)."""
    py_bin = str(Path(sys.executable).resolve())
    click.echo(f"python binary: {py_bin}")
    try:
        n = sum(1 for _ in TRASH_DIR.iterdir())
    except PermissionError as e:
        click.echo(f"  READ: BLOCKED by macOS TCC: {e}", err=True)
        click.echo(f"  Grant Full Disk Access to the python binary above.",
                   err=True)
        sys.exit(1)
    click.echo(f"  READ: OK ({n} entries visible in {TRASH_DIR})")
    # Also check: has the daemon emitted any read_error events?
    if LOG_PATH.exists():
        err_count = sum(1 for line in LOG_PATH.read_text().splitlines()
                        if '"event": "read_error"' in line)
        if err_count:
            click.echo(f"  DAEMON HISTORY: {err_count} read_error events — "
                       f"the daemon has been blocked by TCC in the past.",
                       err=True)
            sys.exit(1)
    click.echo("  DAEMON HISTORY: clean")


@daemon.command("uninstall")
def daemon_uninstall():
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST_DST)], check=False)
    if PLIST_DST.exists():
        PLIST_DST.unlink()
    click.echo(f"uninstalled: {PLIST_DST}")


@daemon.command("status")
def daemon_status():
    uid = os.getuid()
    r = subprocess.run(["launchctl", "print", f"gui/{uid}/{LABEL}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        click.echo("not loaded. Run: trashlog daemon install")
        sys.exit(1)
    click.echo(r.stdout)


if __name__ == "__main__":
    cli()
