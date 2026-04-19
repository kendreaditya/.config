#!/usr/bin/env python3
"""
halflife - mark files with expiration timestamps; sweep moves them to Trash.

Stores Unix epoch (11-digit zero-padded) in the xattr
`com.apple.metadata:hl_expires`. The com.apple.metadata: prefix causes
Spotlight to index the value for existence queries — `mdfind
"hl_expires == '*'"` returns every marked file on the machine in
milliseconds, so we enumerate via Spotlight and filter epochs in Python.
Spotlight won't do numeric comparisons on custom xattrs; the 11-digit
padding is defensive in case an .mdimporter schema is ever added.

Subcommands:
  mark <file> --in DURATION | --at ISODATE   set an expiration
  show <file>                                  print expiration + time left
  list [--expired] [--sort path|expires]       list all marked files
  extend <file> DURATION                       push expiration out
  unmark <file>                                remove the xattr
  sweep [--dry-run] [--deep]                   send expired files to Trash
  daemon install | uninstall | status          manage the 9am launchd agent

Duration: <int><s|m|h|d|w|y>  e.g. 30m, 7d, 2w, 1y
"""
import os
import sys

# re-exec under the config venv so click / osxmetadata are importable
_VENV = os.path.expanduser("~/.config/config-venv")
if os.path.exists(f"{_VENV}/bin/python3") and not sys.prefix.startswith(_VENV):
    os.execv(f"{_VENV}/bin/python3", [f"{_VENV}/bin/python3"] + sys.argv)

import fcntl
import json
import plistlib
import re
import shutil
import subprocess
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import click
from osxmetadata import OSXMetaData


__version__ = "2.0.0"

XATTR = "com.apple.metadata:hl_expires"      # com.apple.metadata: prefix → auto-indexed by Spotlight
XATTR_MARKED_AT = "com.apple.metadata:hl_marked_at"  # audit: when the mark was set
PAD_WIDTH = 11                                # epoch fits in 11 digits until year 5138

LAUNCHD_LABEL = "com.kendreaditya.halflife"
PLIST_DST = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"

CONFIG_DIR = Path.home() / ".config" / "halflife"
CONFIG_PATH = CONFIG_DIR / "config.toml"
LOG_DIR = CONFIG_DIR / "logs"
AUDIT_LOG = LOG_DIR / "sweep.log"
SWEEP_LOCK = CONFIG_DIR / "sweep.lock"
LOG_ROTATE_BYTES = 1 << 20  # 1 MiB

DEFAULT_CONFIG_TOML = """\
# halflife config (v2). Reload by restarting the daemon or re-running commands.

# Paths that require `sudo halflife mark ...` to override.
# Marking within these trees without sudo is refused.
denylist = [
  "/System",
  "/Library",
  "/Applications",
  "~/.ssh",
  "~/.config",
  "~/Documents",
  "~/Pictures",
  "~/Library/Mobile Documents",  # iCloud Drive
]

# Skip sweeping files whose mtime/atime is within this window ("0" to disable).
grace = "24h"

[mark]
# Recursive mark or folder mark hitting more than these limits needs --yes.
max_files_without_confirm = 20
max_bytes_without_confirm = 104857600  # 100 MiB

[logs]
# Rotate daemon + audit logs once they exceed this size.
max_size_bytes = 1048576  # 1 MiB
"""


def _bplist_encode(s: str) -> bytes:
    return plistlib.dumps(s, fmt=plistlib.FMT_BINARY)


def _bplist_decode(b: bytes):
    return plistlib.loads(b)


def _ensure_config_dir() -> None:
    """First-run: create ~/.config/halflife/{config.toml,logs/}."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG_TOML)


def _rotate_log(path: Path, max_bytes: int = LOG_ROTATE_BYTES) -> None:
    """If `path` is larger than `max_bytes`, rename it to `.old` (overwrite prior)."""
    try:
        if path.exists() and path.stat().st_size > max_bytes:
            path.replace(path.with_suffix(path.suffix + ".old"))
    except OSError:
        pass  # log rotation must never crash the caller


def _audit_log(action: str, path: str, *, epoch: int | None = None,
               outcome: str = "ok", dry_run: bool = False,
               detail: str = "") -> None:
    """Append a JSONL record to ~/.config/halflife/logs/sweep.log."""
    try:
        _ensure_config_dir()
        _rotate_log(AUDIT_LOG)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "action": action,
            "path": path,
            "epoch": epoch,
            "outcome": outcome,
            "dry_run": dry_run,
        }
        if detail:
            record["detail"] = detail
        with AUDIT_LOG.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # audit log is best-effort — never crash sweep over it


# ── helpers ──────────────────────────────────────────────────────────────────

DURATION_RE = re.compile(r"^([+-]?\d+)([smhdwy])$")
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31557600}


def parse_duration(s: str) -> int:
    """Return seconds for '30m', '7d', etc."""
    m = DURATION_RE.match(s.strip())
    if not m:
        raise click.BadParameter(
            f"{s!r}: expected <int><s|m|h|d|w|y> (e.g. 30m, 7d, 2w, 1y)"
        )
    return int(m.group(1)) * UNITS[m.group(2)]


def parse_iso(s: str, utc: bool = False) -> tuple[int, str]:
    """Parse an ISO datetime. Naive strings default to local tz (or UTC if utc).

    Returns (epoch, resolved_tz_name) so the caller can echo confirmation.
    """
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise click.BadParameter(f"{s!r}: {e}")
    if dt.tzinfo is None:
        if utc:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone()
    tz_name = dt.tzinfo.tzname(dt) or str(dt.tzinfo)
    return int(dt.timestamp()), tz_name


def pad(epoch: int) -> str:
    return f"{epoch:0{PAD_WIDTH}d}"


class HLReadError(Exception):
    """Signal from read_expiry that the mark exists but couldn't be parsed."""
    def __init__(self, kind: str, detail: str = ""):
        self.kind = kind  # "permission" | "corrupt"
        self.detail = detail


def read_expiry(path: str) -> int | None:
    """Return the stored expiry as an int, or None if the file has no mark.

    Raises HLReadError if the xattr exists but is unreadable (permission
    error) or unparseable (corrupt bplist / bad payload). Callers choose
    whether to warn/log.
    """
    try:
        raw = OSXMetaData(path).get_xattr(XATTR, decode=_bplist_decode)
    except KeyError:
        return None  # not marked — expected, silent
    except PermissionError as e:
        raise HLReadError("permission", str(e))
    except OSError as e:
        # file gone mid-query, other IO issue — treat as "not marked" but note
        if getattr(e, "errno", None) in (2, 93):  # ENOENT, ENOATTR
            return None
        raise HLReadError("permission", str(e))
    except Exception as e:  # malformed bplist, etc.
        raise HLReadError("corrupt", str(e))
    if not raw:
        return None
    try:
        return int(str(raw).lstrip("0") or "0")
    except ValueError as e:
        raise HLReadError("corrupt", f"non-integer value: {raw!r}")


def safe_read_expiry(path: str) -> int | None:
    """read_expiry but log-and-swallow read errors (for bulk scans)."""
    try:
        return read_expiry(path)
    except HLReadError as e:
        _audit_log("read", path, outcome=e.kind, detail=e.detail)
        click.echo(f"warning: {path}: {e.kind}: {e.detail}", err=True)
        return None


def write_expiry(path: str, epoch: int) -> None:
    md = OSXMetaData(path)
    md.set_xattr(XATTR, pad(epoch), encode=_bplist_encode)
    # Also stamp when the mark was written. Best-effort — if the second write
    # fails (read-only target?), we don't roll back the primary xattr.
    try:
        md.set_xattr(XATTR_MARKED_AT, pad(int(time.time())), encode=_bplist_encode)
    except OSError:
        pass


def read_marked_at(path: str) -> int | None:
    """Return the mark-set-time epoch, or None if missing/unreadable."""
    try:
        raw = OSXMetaData(path).get_xattr(XATTR_MARKED_AT, decode=_bplist_decode)
    except (KeyError, OSError, Exception):
        return None
    if not raw:
        return None
    try:
        return int(str(raw).lstrip("0") or "0")
    except ValueError:
        return None


def clear_expiry(path: str) -> None:
    md = OSXMetaData(path)
    for attr in (XATTR, XATTR_MARKED_AT):
        try:
            md.remove_xattr(attr)
        except (KeyError, OSError):
            pass


def fmt_delta(seconds: int) -> str:
    neg = seconds < 0
    seconds = abs(seconds)
    for unit, n in (("y", 31557600), ("w", 604800), ("d", 86400),
                    ("h", 3600), ("m", 60)):
        if seconds >= n:
            num = f"{seconds / n:.1f}".rstrip("0").rstrip(".")
            s = f"{num}{unit}"
            return f"-{s}" if neg else s
    return f"-{seconds}s" if neg else f"{seconds}s"


def mdfind_marked() -> list[str]:
    """Return every path Spotlight knows has an hl_expires mark.

    Spotlight indexes custom com.apple.metadata: xattrs for existence
    queries (`== '*'`) but not for numeric comparisons (`<=`). So we
    enumerate via Spotlight and filter epochs in Python — still O(K)
    where K is the count of marked files on the machine.
    """
    try:
        out = subprocess.run(
            ["mdfind", "hl_expires == '*'"],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout
    except Exception:
        return []
    return [p for p in out.splitlines() if p]


def _local_mounts() -> list[str]:
    """Return filesystem roots that halflife should deep-crawl.

    Always includes $HOME. Adds any local apfs/hfs volume mounted under
    /Volumes (external drives) but skips Recovery/Preboot/VM partitions,
    Time Machine snapshots, and network mounts (smbfs, nfs, afp, fuse).
    """
    roots = [str(Path.home())]
    try:
        out = subprocess.run(["mount"], capture_output=True, text=True,
                             timeout=10, check=False).stdout
    except Exception:
        return roots
    OK_FS = {"apfs", "hfs"}
    SKIP_KEYWORDS = ("Recovery", "Preboot", "Update", "TimeMachine",
                     ".timemachine", "Snapshot", "com.apple.TMSafetyNet")
    seen = set(roots)
    for line in out.splitlines():
        # Format: "<device> on <path> (<fs>, flag1, flag2, ...)"
        m = re.match(r"^\S+\s+on\s+(.+?)\s+\(([^)]+)\)\s*$", line)
        if not m:
            continue
        mount_pt, props = m.group(1), m.group(2)
        parts = [p.strip() for p in props.split(",")]
        fs = parts[0] if parts else ""
        flags = set(parts[1:])
        if fs not in OK_FS:
            continue
        if "local" not in flags:
            continue
        if any(kw in mount_pt for kw in SKIP_KEYWORDS):
            continue
        # Only crawl external mounts under /Volumes; / is covered by $HOME.
        if not mount_pt.startswith("/Volumes/"):
            continue
        if mount_pt not in seen:
            roots.append(mount_pt)
            seen.add(mount_pt)
    return roots


def find_marked_deep(root: str | None = None) -> list[str]:
    """Fallback: filesystem crawl for the xattr. Slow but authoritative.

    If `root` is given, crawls only that path. Otherwise crawls $HOME
    plus every eligible local mount from `_local_mounts()`.
    """
    roots = [root] if root else _local_mounts()
    results: list[str] = []
    for r in roots:
        try:
            out = subprocess.run(
                ["find", r, "-xattrname", XATTR],
                capture_output=True, text=True, timeout=600, check=False,
            ).stdout
        except Exception:
            continue
        results.extend(p for p in out.splitlines() if p)
    return results


def require_trash() -> str:
    path = shutil.which("trash")
    if not path:
        click.echo("halflife: `trash` not on PATH. Run `brew install trash`.", err=True)
        sys.exit(1)
    return path


def _halflife_executable() -> str:
    """Absolute path to the halflife entry point for launchd to invoke."""
    path = shutil.which("halflife")
    if path:
        return path
    # fallback: realpath of whatever invoked us
    try:
        resolved = Path(sys.argv[0]).resolve()
        if resolved.exists():
            return str(resolved)
    except (OSError, RuntimeError):
        pass
    # last resort: the module file itself (launchd will still execute via shebang)
    return str(Path(__file__).resolve())


def _build_launchd_plist() -> dict:
    """Construct the launchd agent definition, using live runtime paths."""
    return {
        "Label": LAUNCHD_LABEL,
        "ProgramArguments": [_halflife_executable(), "sweep"],
        "StartCalendarInterval": {"Hour": 9, "Minute": 0},
        "RunAtLoad": False,
        "StandardOutPath": str(LOG_DIR / "daemon.out"),
        "StandardErrorPath": str(LOG_DIR / "daemon.err"),
    }


def resolve(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        raise click.BadParameter(f"{path!r}: no such file")
    return str(p.resolve())


# ── config loader + guardrails ──────────────────────────────────────────────

_CONFIG_CACHE: dict | None = None


def load_config() -> dict:
    """Read ~/.config/halflife/config.toml, fall back to built-in defaults."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        _CONFIG_CACHE = tomllib.loads(CONFIG_PATH.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        _CONFIG_CACHE = tomllib.loads(DEFAULT_CONFIG_TOML)
    return _CONFIG_CACHE


def is_denylisted(path: Path, denylist: list[str]) -> bool:
    """True if `path` is inside any denylist entry."""
    try:
        abs_target = path.resolve()
    except (OSError, RuntimeError):
        return False
    for entry in denylist:
        try:
            entry_path = Path(entry).expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        try:
            abs_target.relative_to(entry_path)
            return True
        except ValueError:
            continue
        # Also cover the case where abs_target == entry_path exactly
        if abs_target == entry_path:
            return True
    return False


def _walk_files(root: Path):
    """Yield every regular file under `root` (skips symlinks by default)."""
    for p in root.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                yield p
        except OSError:
            continue


# ── wrap helpers ────────────────────────────────────────────────────────────

# Directories and file patterns that are *regenerable* from source: marking them
# adds noise to `halflife list` without providing value, since rerunning the
# build step recreates them. `halflife wrap` skips these by default; pass
# --follow-regenerable to mark them anyway.
REGENERABLE_DIR_NAMES = frozenset({
    "node_modules", ".venv", "venv", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "target",                                      # rust
    "build", "dist", "_build",                     # python/node/docs
    ".next", ".nuxt", ".svelte-kit", ".turbo",     # js frameworks
    ".cache",
    ".git",                                        # obvious
})
REGENERABLE_FILE_NAMES = frozenset({".DS_Store"})
REGENERABLE_SUFFIXES = frozenset({".pyc", ".pyo"})


def _is_regenerable_path(p: Path, root: Path) -> bool:
    """True if `p` lives under / matches a regenerable pattern relative to `root`."""
    try:
        rel = p.relative_to(root)
    except ValueError:
        return False
    if any(part in REGENERABLE_DIR_NAMES for part in rel.parts):
        return True
    if p.name in REGENERABLE_FILE_NAMES:
        return True
    if p.suffix in REGENERABLE_SUFFIXES:
        return True
    return False


def _snapshot_files(root: Path) -> dict:
    """Return {(dev, ino): path} for every regular file under `root`.

    Keying by (dev, ino) means renames/moves within the tree aren't counted as
    new; only files that weren't physically present before show up as diffs.
    """
    snap: dict[tuple[int, int], Path] = {}
    for p in root.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                st = p.stat()
                snap[(st.st_dev, st.st_ino)] = p
        except OSError:
            continue
    return snap


# ── CLI ──────────────────────────────────────────────────────────────────────

@click.group(help=__doc__)
@click.version_option(__version__, prog_name="halflife")
def cli():
    pass


@cli.command()
@click.argument("file", type=click.Path())
@click.option("--in", "in_", metavar="DURATION", help="e.g. 30m, 7d, 2w, 1y")
@click.option("--at", "at", metavar="ISODATE", help="e.g. 2026-05-01 or 2026-05-01T09:00")
@click.option("-r", "--recursive", is_flag=True,
              help="If FILE is a directory, mark every file inside it individually.")
@click.option("--tree", is_flag=True,
              help="If FILE is a directory, mark the folder itself. Sweep will "
                   "trash the whole tree. Opaque but more efficient than -r.")
@click.option("--yes", is_flag=True,
              help="Skip confirmation when marking many files (see config).")
@click.option("--follow", is_flag=True,
              help="If FILE is a symlink, mark the resolved target.")
@click.option("--utc", is_flag=True,
              help="Interpret --at as UTC when no tz is given (default: local).")
def mark(file, in_, at, recursive, tree, yes, follow, utc):
    """Set an expiration timestamp on FILE (or FILEs under it)."""
    if bool(in_) == bool(at):
        raise click.UsageError("specify exactly one of --in or --at")
    if recursive and tree:
        raise click.UsageError("-r and --tree are mutually exclusive")
    if utc and not at:
        raise click.UsageError("--utc is only meaningful with --at")

    raw = Path(file).expanduser()
    if not raw.exists() and not raw.is_symlink():
        raise click.BadParameter(f"{file!r}: no such file")

    # Symlinks: refuse silently-follow to protect against "I marked the link
    # but the target got trashed." --follow makes the intent explicit.
    if raw.is_symlink() and not follow:
        click.echo(
            f"{raw}: is a symlink. Pass --follow to mark the target, or run "
            f"against the resolved path directly.",
            err=True,
        )
        sys.exit(1)
    target = raw.resolve()

    # Denylist sudo wall
    cfg = load_config()
    if is_denylisted(target, cfg.get("denylist", [])) and os.geteuid() != 0:
        click.echo(
            f"{target}: path is denylisted. Re-run with `sudo halflife mark ...` "
            f"to override, or remove the match from ~/.config/halflife/config.toml.",
            err=True,
        )
        sys.exit(1)

    # Pick the set of things to mark
    if target.is_dir():
        if not (recursive or tree):
            click.echo(
                f"{target}: is a directory. This is dangerous — sweep would trash "
                f"the whole tree.\n"
                f"  Use `-r` to mark each contained file individually "
                f"(safer, visible in `list`), or\n"
                f"  Use `--tree` to mark the folder itself "
                f"(destructive: sweep moves the entire tree to Trash).",
                err=True,
            )
            sys.exit(1)
        if recursive:
            targets = list(_walk_files(target))
            if not targets:
                click.echo(f"{target}: empty (no files to mark)", err=True)
                sys.exit(1)
        else:  # --tree
            targets = [target]
    else:
        targets = [target]

    # Threshold gate (only for recursive; --tree is inherently one inode)
    if recursive and not yes:
        mark_cfg = cfg.get("mark", {})
        max_files = int(mark_cfg.get("max_files_without_confirm", 20))
        max_bytes = int(mark_cfg.get("max_bytes_without_confirm", 100 * 1024 * 1024))
        total_bytes = 0
        for t in targets:
            try:
                total_bytes += t.stat().st_size
            except OSError:
                pass
        if len(targets) > max_files or total_bytes > max_bytes:
            click.echo(
                f"About to mark {len(targets)} files totaling "
                f"{total_bytes / (1 << 20):.1f} MiB under {target}.\n"
                f"Re-run with `--yes` to confirm.",
                err=True,
            )
            sys.exit(1)

    tz_note = ""
    if in_:
        epoch = int(time.time()) + parse_duration(in_)
    else:
        epoch, tz_name = parse_iso(at, utc=utc)
        tz_note = f" [{tz_name}]"
    when = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S") + tz_note
    delta = fmt_delta(epoch - int(time.time()))

    # For a single target, surface "was X → now Y" when overwriting.
    prior: int | None = None
    if len(targets) == 1:
        try:
            prior = read_expiry(str(targets[0]))
        except HLReadError:
            prior = None

    marked = 0
    failures = 0
    for t in targets:
        try:
            write_expiry(str(t), epoch)
            marked += 1
        except OSError as e:
            click.echo(f"skip: {t}: {e}", err=True)
            failures += 1

    if len(targets) == 1:
        if prior is not None:
            was = datetime.fromtimestamp(prior).strftime("%Y-%m-%d %H:%M:%S")
            click.echo(f"refreshed: {targets[0]}\n  was: {was}\n  now: {when} ({delta})")
        else:
            click.echo(f"marked: {targets[0]}\n  expires: {when} ({delta})")
    else:
        click.echo(
            f"marked: {marked} file{'s' if marked != 1 else ''} under {target}\n"
            f"  expires: {when} ({delta})"
            + (f"\n  skipped: {failures}" if failures else "")
        )


@cli.command(context_settings={"ignore_unknown_options": True,
                                "allow_interspersed_args": False})
@click.option("--in", "in_", default="14d", show_default=True,
              metavar="DURATION",
              help="Expiration for files the command creates.")
@click.option("--watch", "watch_dir", default=None, metavar="DIR",
              help="Watch this directory instead of the current working dir.")
@click.option("--yes", is_flag=True,
              help="Skip confirmation if many files / much data get captured.")
@click.option("--follow-regenerable", is_flag=True,
              help="Also mark files under node_modules/.venv/__pycache__/etc. "
                   "(default: skip regenerable dirs).")
@click.option("--quiet", is_flag=True,
              help="Suppress the summary line after the command completes.")
@click.argument("argv", nargs=-1, type=click.UNPROCESSED, required=True)
def wrap(in_, watch_dir, yes, follow_regenerable, quiet, argv):
    """Run COMMAND; mark any new files it creates with an expiration.

    The intent primitive: you know this command's output is exploratory, so
    you prefix it with `halflife wrap` (or an alias like `hl-try`). We
    snapshot the working directory before and after the command, mark any
    new files with the given expiration, and preserve the command's exit
    code.

    Examples:
      halflife wrap --in 14d curl -O https://example.com/weights.bin
      halflife wrap --in 7d  -- python train.py
      halflife wrap --in 30d --watch ~/scratch -- git clone https://…
    """
    if not argv:
        raise click.UsageError("wrap needs a command to run")

    watch = Path(watch_dir).expanduser().resolve() if watch_dir else Path.cwd()
    if not watch.is_dir():
        raise click.UsageError(f"{watch}: not a directory")

    seconds = parse_duration(in_)  # fail fast on bad duration

    before = _snapshot_files(watch)

    # Run the command transparently: inherit stdin/stdout/stderr so tty
    # behavior, colors, progress bars etc. work normally.
    try:
        rc = subprocess.call(list(argv))
    except FileNotFoundError as e:
        click.echo(f"wrap: command not found: {e}", err=True)
        sys.exit(127)

    after = _snapshot_files(watch)
    new_keys = set(after.keys()) - set(before.keys())
    new_paths = [after[k] for k in new_keys]

    if not follow_regenerable:
        new_paths = [p for p in new_paths if not _is_regenerable_path(p, watch)]

    if not new_paths:
        if not quiet:
            click.echo(f"wrap: no new files to mark under {watch}", err=True)
        sys.exit(rc)

    # Threshold gate (shared with `mark -r`)
    if not yes:
        cfg = load_config()
        mark_cfg = cfg.get("mark", {})
        max_files = int(mark_cfg.get("max_files_without_confirm", 20))
        max_bytes = int(mark_cfg.get("max_bytes_without_confirm", 100 * 1024 * 1024))
        total_bytes = 0
        for p in new_paths:
            try:
                total_bytes += p.stat().st_size
            except OSError:
                pass
        if len(new_paths) > max_files or total_bytes > max_bytes:
            click.echo(
                f"wrap: command created {len(new_paths)} new files totaling "
                f"{total_bytes / (1 << 20):.1f} MiB under {watch}.\n"
                f"Re-run with --yes to confirm marking them.",
                err=True,
            )
            # Preserve the command's exit code if it failed; otherwise exit 1
            # to signal we skipped the marking step.
            sys.exit(rc if rc != 0 else 1)

    epoch = int(time.time()) + seconds
    when = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
    delta = fmt_delta(seconds)

    marked = skipped_err = 0
    for p in new_paths:
        try:
            write_expiry(str(p), epoch)
            marked += 1
        except OSError:
            skipped_err += 1

    if not quiet:
        click.echo(
            f"wrap: marked {marked} file{'s' if marked != 1 else ''} "
            f"expiring {when} ({delta})"
            + (f", skipped {skipped_err} (errors)" if skipped_err else ""),
            err=True,
        )

    sys.exit(rc)


@cli.command()
@click.argument("file", type=click.Path())
def show(file):
    """Print FILE's expiration, or nothing if unmarked."""
    path = resolve(file)
    try:
        epoch = read_expiry(path)
    except HLReadError as e:
        click.echo(f"{path}: xattr {e.kind} error: {e.detail}", err=True)
        sys.exit(2)
    if epoch is None:
        click.echo(f"{path}: not marked")
        sys.exit(1)
    now = int(time.time())
    when = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
    status = "EXPIRED" if epoch <= now else "pending"
    click.echo(f"{path}\n  expires: {when}  ({fmt_delta(epoch - now)}, {status})")
    marked_at = read_marked_at(path)
    if marked_at is not None:
        ago = fmt_delta(now - marked_at)
        stamped = datetime.fromtimestamp(marked_at).strftime("%Y-%m-%d %H:%M:%S")
        click.echo(f"  marked:  {stamped}  ({ago} ago)")


@cli.command(name="list")
@click.option("--expired", is_flag=True, help="only files whose timer has elapsed")
@click.option("--sort", "sort_by", type=click.Choice(["path", "expires"]),
              default="expires")
@click.option("--deep", is_flag=True, help="filesystem crawl instead of mdfind")
@click.option("--json", "as_json", is_flag=True,
              help="Emit one JSON record per line (JSONL).")
def list_cmd(expired, sort_by, deep, as_json):
    """List all marked files."""
    paths = find_marked_deep() if deep else mdfind_marked()
    rows = []
    now = int(time.time())
    for p in paths:
        epoch = safe_read_expiry(p)
        if epoch is None:
            continue
        if expired and epoch > now:
            continue
        rows.append((p, epoch))
    rows.sort(key=lambda r: r[1] if sort_by == "expires" else r[0])
    if not rows:
        if not as_json:
            click.echo("(no marked files found)", err=True)
        return
    for p, epoch in rows:
        if as_json:
            click.echo(json.dumps({
                "path": p,
                "expires_epoch": epoch,
                "expires_iso": datetime.fromtimestamp(epoch, timezone.utc)
                                       .isoformat(timespec="seconds"),
                "seconds_until_expiry": epoch - now,
                "status": "expired" if epoch <= now else "pending",
                "marked_at_epoch": read_marked_at(p),
            }))
        else:
            when = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")
            click.echo(f"{when}  {fmt_delta(epoch - now):>8}  {p}")


@cli.command()
@click.argument("file", type=click.Path())
@click.argument("duration")
@click.option("--from", "from_", type=click.Choice(["now", "current"]),
              default=None,
              help="Base for the new expiry: 'now' (default if expired) "
                   "or 'current' stored expiry (default if pending).")
def extend(file, duration, from_):
    """Push FILE's expiration out by DURATION (e.g. 3d, 2w)."""
    path = resolve(file)
    try:
        current = read_expiry(path)
    except HLReadError as e:
        click.echo(f"{path}: xattr {e.kind} error: {e.detail}", err=True)
        sys.exit(2)
    if current is None:
        click.echo(f"{path}: not marked. Use `halflife mark` first.", err=True)
        sys.exit(1)
    now = int(time.time())
    delta = parse_duration(duration)
    # Default base: "now" if already expired (avoids the "still expired after
    # extend" footgun), "current" otherwise. --from overrides either way.
    if from_ is None:
        base_name = "now" if current < now else "current"
    else:
        base_name = from_
    base = now if base_name == "now" else current
    new_epoch = base + delta
    write_expiry(path, new_epoch)
    when = datetime.fromtimestamp(new_epoch).strftime("%Y-%m-%d %H:%M:%S")
    was = datetime.fromtimestamp(current).strftime("%Y-%m-%d %H:%M:%S")
    note = f" (base=now; file was expired)" if base_name == "now" and current < now else ""
    click.echo(f"extended: {path}\n  was: {was}\n  now: {when}{note}")


@cli.command()
@click.argument("file", type=click.Path())
def unmark(file):
    """Remove FILE's expiration mark."""
    path = resolve(file)
    if safe_read_expiry(path) is None:
        click.echo(f"{path}: not marked")
        return
    clear_expiry(path)
    click.echo(f"unmarked: {path}")


@cli.command()
@click.option("--dry-run", is_flag=True, help="print what would be trashed")
@click.option("--deep", is_flag=True,
              help="fall back to `find` crawl if mdfind looks empty")
@click.option("--grace", default=None, metavar="DURATION",
              help="Skip files modified within this window. "
                   "Default from config.toml (24h); `--grace 0` disables.")
@click.option("--json", "as_json", is_flag=True,
              help="Emit one JSON record per line (JSONL).")
def sweep(dry_run, deep, grace, as_json):
    """Move expired files to Trash."""
    _ensure_config_dir()
    _rotate_log(AUDIT_LOG)  # rotate once per invocation, even on empty sweeps

    # Resolve grace period: CLI overrides config; config defaults to "24h".
    cfg = load_config()
    grace_str = grace if grace is not None else cfg.get("grace", "24h")
    try:
        grace_seconds = parse_duration(grace_str) if grace_str not in ("0", "0s") else 0
    except click.BadParameter:
        click.echo(f"sweep: invalid grace duration {grace_str!r}", err=True)
        sys.exit(2)

    # Serialize sweeps across processes (manual run + launchd cron could race).
    lock_fd = open(SWEEP_LOCK, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        click.echo("sweep: another halflife sweep is already running. Exiting.",
                   err=True)
        sys.exit(1)

    try:
        trash = None if dry_run else require_trash()
        now = int(time.time())
        grace_cutoff = now - grace_seconds

        # Enumerate via Spotlight (fast) or full filesystem crawl (slow, --deep).
        # Filter epochs in Python (Spotlight can't do numeric compares on
        # custom xattrs). We trust mdfind; if you suspect the index is stale,
        # pass --deep explicitly.
        paths = find_marked_deep() if deep else mdfind_marked()
        candidates = [p for p in paths
                      if (e := safe_read_expiry(p)) is not None and e <= now]

        def emit(action: str, path: str, **extra):
            if as_json:
                rec = {"action": action, "path": path, "dry_run": dry_run, **extra}
                click.echo(json.dumps(rec))
            else:
                prefix = {
                    "trash": "would trash: " if dry_run else "trashed: ",
                    "skip_grace": "skip (grace): ",
                    "skip_stale": "skip: ",
                    "error": "error: ",
                }.get(action, f"{action}: ")
                msg = prefix + path
                if "detail" in extra:
                    msg += f" ({extra['detail']})"
                click.echo(msg, err=(action == "error"))

        swept = skipped = errors = 0
        for path in candidates:
            # re-verify live — guards against race + stale index
            epoch = safe_read_expiry(path)
            if epoch is None or epoch > now:
                skipped += 1
                _audit_log("skip", path, epoch=epoch, outcome="not_expired",
                           dry_run=dry_run)
                emit("skip_stale", path, reason="not_expired")
                continue
            if grace_seconds > 0:
                try:
                    mtime = os.stat(path).st_mtime
                except OSError:
                    mtime = 0
                if mtime > grace_cutoff:
                    age = now - int(mtime)
                    _audit_log("skip", path, epoch=epoch, outcome="grace",
                               dry_run=dry_run, detail=f"mtime_age={age}s")
                    emit("skip_grace", path,
                         detail=f"modified {fmt_delta(age)} ago",
                         reason="grace", mtime_age_seconds=age)
                    skipped += 1
                    continue
            if dry_run:
                emit("trash", path, epoch=epoch)
                _audit_log("trash", path, epoch=epoch, outcome="ok", dry_run=True)
                swept += 1
                continue
            try:
                subprocess.run([trash, path], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                emit("trash", path, epoch=epoch)
                _audit_log("trash", path, epoch=epoch, outcome="ok")
                swept += 1
            except subprocess.CalledProcessError as e:
                detail = e.stderr.decode().strip()
                emit("error", path, detail=detail)
                _audit_log("trash", path, epoch=epoch, outcome="error",
                           detail=detail)
                errors += 1

        summary = {"swept": swept, "skipped": skipped, "errors": errors}
        if as_json:
            click.echo(json.dumps({"action": "summary", **summary}))
        else:
            click.echo(f"\nswept {swept}, skipped {skipped}, errors {errors}",
                       err=True)
            if not paths and not deep:
                click.echo("(tip: Spotlight returned 0 marks. "
                           "`halflife sweep --deep` crawls the filesystem "
                           "directly.)", err=True)
        if errors > 0:
            sys.exit(1)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


@cli.group()
def daemon():
    """Manage the launchd agent (daily 9am sweep)."""


@daemon.command("install")
def daemon_install():
    _ensure_config_dir()  # LOG_DIR must exist before launchd writes to it
    PLIST_DST.parent.mkdir(parents=True, exist_ok=True)
    with open(PLIST_DST, "wb") as f:
        plistlib.dump(_build_launchd_plist(), f)
    uid = os.getuid()
    # unload first in case it's already loaded
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST_DST)],
                   check=False, stderr=subprocess.DEVNULL)
    r = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(PLIST_DST)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        click.echo(f"bootstrap failed: {r.stderr.strip()}", err=True)
        sys.exit(1)
    click.echo(f"installed: {PLIST_DST}\n"
               f"  executable: {_halflife_executable()}\n"
               f"  logs: {LOG_DIR}/daemon.{{out,err}}\n"
               f"  next run: daily 09:00 local time")


@daemon.command("uninstall")
def daemon_uninstall():
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST_DST)],
                   check=False)
    if PLIST_DST.exists():
        PLIST_DST.unlink()
    click.echo(f"uninstalled: {PLIST_DST}")


@daemon.command("status")
def daemon_status():
    uid = os.getuid()
    r = subprocess.run(
        ["launchctl", "print", f"gui/{uid}/{LAUNCHD_LABEL}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        click.echo("not loaded. Run: halflife daemon install")
        sys.exit(1)
    click.echo(r.stdout)


if __name__ == "__main__":
    cli()
