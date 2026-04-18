#!/usr/bin/env python3
"""Meta / setup / config commands: init, doctor, config-get/set, version, graph(s), use.

Only `init` is interactive. Exports: HANDLERS dict + register(subparsers).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from _logseq_common import (  # noqa: E402
    CONFIG_FILE, LogseqError, Session,
    call, err, load_session, out, save_config, set_session,
)

CLI_VERSION = "0.1.0"


# ---------- init ----------

def cmd_init(args: argparse.Namespace, session: Session) -> int:
    """Interactive setup: prompt for token/host/port, test connection, save config."""
    err("Interactive setup for logseq CLI.\n")
    try:
        token = input("API token: ").strip()
        host = input("Host [127.0.0.1]: ").strip() or "127.0.0.1"
        port_s = input("Port [12315]: ").strip()
    except (EOFError, KeyboardInterrupt):
        err("\naborted")
        return 1
    try:
        port = int(port_s) if port_s else 12315
    except ValueError:
        err(f"bad port: {port_s!r}")
        return 4

    err(f"Testing connection to {host}:{port}...")
    probe_ns = argparse.Namespace(
        token=token, host=host, port=port, graph=None,
        fmt="json", limit=None, offset=None, yes=False, dry_run=False,
        verbose=False, quiet=False, uuids_only=False,
    )
    probe_s = load_session(probe_ns)
    set_session(probe_s)

    try:
        info = call("logseq.App.getAppInfo") or {}
        graph = call("logseq.App.getCurrentGraph") or {}
    except LogseqError as e:
        err(f"Connection test failed ({e.kind}): {e.message}")
        return e.exit_code
    except Exception as e:
        err(f"Connection test failed: {e}")
        return 1

    err(f"  OK  Logseq {info.get('version')} at {host}:{port}")
    err(f"  OK  Current graph: {graph.get('name')}")

    save_config({"token": token, "host": host, "port": port, "graph": None})
    err(f"\nSaved to {CONFIG_FILE} (chmod 600).")
    err("Run `logseq doctor` to verify, or `logseq today` to start.")
    return 0


# ---------- doctor ----------

def cmd_doctor(args: argparse.Namespace, session: Session) -> int:
    """Diagnose the CLI setup. --fix also chmods + symlinks the entry script."""
    err(f"[doctor] Config: {CONFIG_FILE}")
    err(f"[doctor] {'exists' if CONFIG_FILE.exists() else 'MISSING'}")

    try:
        info = call("logseq.App.getAppInfo") or {}
        err(f"[doctor] Server: OK, Logseq {info.get('version')} "
            f"at {session.host}:{session.port}")
    except LogseqError as e:
        err(f"[doctor] Server: FAIL ({e.kind}) — {e.message}")
        return e.exit_code

    graph = call("logseq.App.getCurrentGraph") or {}
    err(f"[doctor] Graph: {graph.get('name')} at {graph.get('path')}")
    if session.graph and session.graph != graph.get("name"):
        err(f"[doctor] WARNING: configured graph {session.graph!r} "
            f"!= running graph {graph.get('name')!r}")

    count = call("logseq.DB.datascriptQuery",
                 ['[:find (count ?b) . :where [?b :block/uuid _]]'])
    err(f"[doctor] Blocks: {count}")

    if args.fix:
        script_path = Path(__file__).resolve().parent.parent / "logseq.py"
        target = Path.home() / ".config" / "scripts" / "logseq"
        try:
            if script_path.exists():
                os.chmod(script_path, 0o755)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or target.exists():
                target.unlink()
            target.symlink_to(script_path)
            err(f"[doctor] --fix: symlinked {target} -> {script_path}")
        except Exception as e:
            err(f"[doctor] --fix: symlink failed: {e}")
            return 1

    err("[doctor] OK")
    return 0


# ---------- config-get / config-set ----------

def _redact_token(data: dict) -> dict:
    """Return a copy with token partially masked."""
    d = dict(data)
    t = d.get("token")
    if t:
        t = str(t)
        if len(t) > 4:
            d["token"] = t[:2] + "*" * (len(t) - 4) + t[-2:]
        else:
            d["token"] = "*" * len(t)
    return d


def cmd_config_get(args: argparse.Namespace, session: Session) -> int:
    """Print config (token redacted). If `key` given, print just that value."""
    if not CONFIG_FILE.exists():
        err(f"No config at {CONFIG_FILE}. Run `logseq init`.")
        return 1
    try:
        data = json.loads(CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        err(f"config unreadable: {e}")
        return 1
    data = _redact_token(data)
    if args.key:
        out(data.get(args.key), session=session)
    else:
        out(data, session=session)
    return 0


def cmd_config_set(args: argparse.Namespace, session: Session) -> int:
    """Write a key to config. Coerces `port` to int."""
    value = args.value
    if args.key == "port":
        try:
            value = int(value)
        except ValueError:
            err(f"port must be int, got {value!r}")
            return 4
    save_config({args.key: value})
    out({"key": args.key, "value": value}, session=session)
    return 0


# ---------- version ----------

def cmd_version(args: argparse.Namespace, session: Session) -> int:
    """Print CLI version + Logseq API version."""
    remote = None
    try:
        info = call("logseq.App.getAppInfo") or {}
        remote = info.get("version")
    except LogseqError:
        pass
    out({"cli": CLI_VERSION, "logseq": remote}, session=session)
    return 0


# ---------- graph / graphs / use ----------

def cmd_graph(args: argparse.Namespace, session: Session) -> int:
    """Print the currently-open graph (from getCurrentGraph)."""
    out(call("logseq.App.getCurrentGraph"), session=session)
    return 0


_LOCAL_URL_PREFIX = "logseq_local_"


def _name_from_url(url: str) -> str:
    """Derive a graph name from a `logseq_local_<path>` url when graphName is missing."""
    if not isinstance(url, str):
        return ""
    path = url[len(_LOCAL_URL_PREFIX):] if url.startswith(_LOCAL_URL_PREFIX) else url
    return os.path.basename(path.rstrip("/")) or path


def _path_from_url(url: str) -> str:
    if not isinstance(url, str):
        return ""
    return url[len(_LOCAL_URL_PREFIX):] if url.startswith(_LOCAL_URL_PREFIX) else url


def cmd_graphs(args: argparse.Namespace, session: Session) -> int:
    """List all graphs from user configs. Normalizes local vs remote repo shapes."""
    cfg = call("logseq.App.getUserConfigs") or {}
    repos = (cfg.get("me") or {}).get("repos") or []
    current = call("logseq.App.getCurrentGraph") or {}
    cur_name = current.get("name")
    items = []
    for r in repos:
        if not isinstance(r, dict):
            continue
        name = r.get("graphName") or _name_from_url(r.get("url") or "")
        path = r.get("root") or _path_from_url(r.get("url") or "")
        items.append({
            "name": name,
            "path": path,
            "remote": bool(r.get("remote?")),
            "current": bool(name) and name == cur_name,
        })
    out(items, session=session)
    return 0


def cmd_use(args: argparse.Namespace, session: Session) -> int:
    """Soft-pin a default graph in config. Doesn't switch Logseq itself."""
    save_config({"graph": args.name})
    err(f"Soft-pinned graph to {args.name!r}. Logseq must be switched to this "
        "graph manually — the HTTP API doesn't support switching graphs.")
    out({"graph": args.name}, session=session)
    return 0


# ---------- module exports ----------

HANDLERS = {
    "init": cmd_init, "doctor": cmd_doctor,
    "config-get": cmd_config_get, "config-set": cmd_config_set,
    "version": cmd_version, "graph": cmd_graph, "graphs": cmd_graphs,
    "use": cmd_use,
}


def register(subparsers) -> None:
    """Attach meta subparsers. Coordinator calls this during argparse setup."""
    p = subparsers.add_parser("init", help="Interactive setup (prompt + save config)")
    p.set_defaults(func=cmd_init)
    p = subparsers.add_parser("doctor", help="Diagnose + optionally --fix (symlink)")
    p.add_argument("--fix", action="store_true",
                   help="chmod + symlink ~/.config/scripts/logseq")
    p.set_defaults(func=cmd_doctor)
    p = subparsers.add_parser("config-get", help="Print config (token redacted)")
    p.add_argument("key", nargs="?", help="Single key (omit for full config)")
    p.set_defaults(func=cmd_config_get)
    p = subparsers.add_parser("config-set", help="Set a config key")
    p.add_argument("key")
    p.add_argument("value")
    p.set_defaults(func=cmd_config_set)
    p = subparsers.add_parser("version", help="CLI + Logseq versions")
    p.set_defaults(func=cmd_version)
    p = subparsers.add_parser("graph", help="Current graph")
    p.set_defaults(func=cmd_graph)
    p = subparsers.add_parser("graphs", help="All graphs from user configs")
    p.set_defaults(func=cmd_graphs)
    p = subparsers.add_parser("use", help="Soft-pin a default graph in config")
    p.add_argument("name", help="graph name")
    p.set_defaults(func=cmd_use)


# ---------- self-test ----------

if __name__ == "__main__":
    import argparse as _ap

    ns = _ap.Namespace(
        token="cc", host="127.0.0.1", port=12315, graph=None,
        fmt="json", limit=None, offset=None, yes=False, dry_run=False,
        verbose=False, quiet=False, uuids_only=False,
    )
    s = load_session(ns)
    set_session(s)

    print("-- version --")
    cmd_version(_ap.Namespace(), s)
    print("-- graph --")
    cmd_graph(_ap.Namespace(), s)
    print("-- graphs --")
    cmd_graphs(_ap.Namespace(), s)
    print("-- config-get (full) --")
    cmd_config_get(_ap.Namespace(key=None), s)
    print("-- config-get token (redacted) --")
    cmd_config_get(_ap.Namespace(key="token"), s)
    print("-- doctor (no --fix) --")
    cmd_doctor(_ap.Namespace(fix=False), s)
    print("All meta.py self-tests done.")
