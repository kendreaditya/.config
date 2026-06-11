#!/usr/bin/env python3
"""
check-noqueue-sessions.py — find RUNNING claude sessions that are executing
stale, unpatched queue logic in memory (and therefore still inject mid-turn
messages), even though the on-disk binary is patched.

WHY THIS IS NEEDED
------------------
repatch-claude-noqueue.sh patches the binary FILE. But a process loads its
code into memory at launch; rewriting the file afterward cannot reach an
already-running process. The SessionStart self-heal hook runs INSIDE the
just-launched process, so its patch only ever helps the NEXT launch — the
current process keeps the bytes it started with for its whole life.

Concrete case that motivated this (2026-06-07): the compass session PID 208
launched at 23:27:40 from 2.1.165's unpatched bytes; the hook patched the file
at 23:28:00 (20s later). PID 208 then kept injecting mid-turn 'prompt'-mode
messages for hours. The only fix is to RESTART that session.

DETECTION
---------
For each running `claude` process:
  exe        = the versions/<X> binary it is executing (via lsof)
  pstart     = when the process started
  bmtime     = mtime of exe (the repatch rewrites the file -> bumps mtime)
  patched    = does exe currently contain the patch tautology `q.mode===q.mode`?

Verdict:
  - exe NOT patched right now            -> STALE  (the bytes are unpatched)
  - exe patched but pstart < bmtime      -> STALE  (loaded PRE-patch bytes;
                                                     patched after it launched)
  - exe patched and pstart >= bmtime     -> OK     (loaded patched bytes)

STALE sessions still interrupt the queue and should be restarted.

USAGE
-----
    check-noqueue-sessions.py            # human table
    check-noqueue-sessions.py --json     # machine-readable
Exit code: 0 if all running sessions are OK, 1 if any are STALE.
"""

import json
import os
import re
import subprocess
import sys
import time

PATCH_FP = b"q.mode===q.mode"          # the patch #2 tautology
VERSION_RE = re.compile(r"versions/[0-9][0-9A-Za-z.\-]*")


def sh(args):
    return subprocess.run(args, capture_output=True, text=True).stdout


def running_claude_pids():
    out = sh(["pgrep", "-f", "claude --dangerously-skip-permissions"])
    pids = []
    for tok in out.split():
        try:
            pids.append(int(tok))
        except ValueError:
            pass
    # also catch sessions launched without that exact flag
    out2 = sh(["pgrep", "-x", "claude"])
    for tok in out2.split():
        try:
            p = int(tok)
            if p not in pids:
                pids.append(p)
        except ValueError:
            pass
    return sorted(set(pids))


def proc_exe(pid):
    """The versions/<X> binary the process is executing, via its txt maps."""
    out = sh(["lsof", "-p", str(pid)])
    for line in out.splitlines():
        m = VERSION_RE.search(line)
        if m and "/versions/" in line:
            # recover the absolute path token
            for tok in line.split():
                if "/versions/" in tok:
                    return tok
    return None


def proc_cwd(pid):
    out = sh(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"])
    for line in out.splitlines():
        if line.startswith("n"):
            return line[1:]
    return None


def proc_start_epoch(pid):
    s = sh(["ps", "-o", "lstart=", "-p", str(pid)]).strip()
    if not s:
        return None
    s = re.sub(r"\s+", " ", s)  # "Jun  6" -> "Jun 6"
    try:
        return time.mktime(time.strptime(s, "%a %b %d %H:%M:%S %Y"))
    except ValueError:
        return None


def is_patched(path):
    try:
        with open(path, "rb") as f:
            return PATCH_FP in f.read()
    except OSError:
        return None


def classify(pid):
    exe = proc_exe(pid)
    cwd = proc_cwd(pid)
    pstart = proc_start_epoch(pid)
    if not exe:
        return {"pid": pid, "cwd": cwd, "exe": None, "verdict": "UNKNOWN",
                "reason": "could not resolve executing binary"}
    ver_early = exe.split("/versions/")[-1] if "/versions/" in exe else exe
    if not os.path.exists(exe):
        # The updater deleted this version's file; the process still runs the
        # deleted inode's bytes in memory. Can't grep it, but a process on a
        # superseded version is running old code by definition -> restart.
        return {"pid": pid, "cwd": cwd, "exe": exe, "version": ver_early,
                "patched_now": None, "pstart": pstart, "bmtime": None,
                "verdict": "GONE",
                "reason": "binary deleted (superseded version); running old "
                          "in-memory code — restart to be safe"}
    patched = is_patched(exe)
    try:
        bmtime = os.path.getmtime(exe)
    except OSError:
        bmtime = None
    ver = exe.split("/versions/")[-1] if "/versions/" in exe else exe

    if patched is False:
        verdict, reason = "STALE", "binary itself is UNPATCHED"
    elif patched is None:
        verdict, reason = "UNKNOWN", "could not read binary"
    elif pstart is not None and bmtime is not None and pstart < bmtime - 1:
        verdict = "STALE"
        reason = (f"loaded PRE-patch bytes (started "
                  f"{time.strftime('%m-%d %H:%M:%S', time.localtime(pstart))}, "
                  f"patched {time.strftime('%m-%d %H:%M:%S', time.localtime(bmtime))})")
    else:
        verdict, reason = "OK", "loaded patched bytes"

    return {"pid": pid, "cwd": cwd, "exe": exe, "version": ver,
            "patched_now": patched, "pstart": pstart, "bmtime": bmtime,
            "verdict": verdict, "reason": reason}


def main():
    as_json = "--json" in sys.argv
    rows = [classify(p) for p in running_claude_pids()]

    if as_json:
        print(json.dumps(rows, indent=2))
    else:
        if not rows:
            print("No running claude sessions found.")
        print(f"{'PID':>6}  {'VER':<10} {'VERDICT':<8} {'CWD':<45} REASON")
        print("-" * 110)
        for r in rows:
            cwd = (r.get("cwd") or "?")
            if len(cwd) > 44:
                cwd = "…" + cwd[-43:]
            mark = {"STALE": "❌", "OK": "✅", "GONE": "⚠️ "}.get(r["verdict"], "•")
            print(f"{r['pid']:>6}  {r.get('version','?'):<10} "
                  f"{mark}{r['verdict']:<7} {cwd:<45} {r['reason']}")
        need_restart = [r for r in rows if r["verdict"] in ("STALE", "GONE")]
        confirmed = [r for r in rows if r["verdict"] == "STALE"]
        print()
        if need_restart:
            print(f"❌ {len(confirmed)} confirmed-stale + "
                  f"{len(need_restart) - len(confirmed)} deleted-binary session(s) "
                  "still inject mid-turn — restart to stop queue interruption:")
            for r in need_restart:
                tag = "stale" if r["verdict"] == "STALE" else "old/deleted"
                print(f"     PID {r['pid']:>6}  {r.get('version','?'):<9} "
                      f"[{tag}]  {r.get('cwd') or '?'}")
        else:
            print("✅ All running sessions are executing patched queue logic.")

    sys.exit(1 if any(r["verdict"] in ("STALE", "GONE") for r in rows) else 0)


if __name__ == "__main__":
    main()
