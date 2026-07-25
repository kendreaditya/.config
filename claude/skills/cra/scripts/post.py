"""Post the rendered review body as a PR comment via gh.

Usage:
  post.py <pr-url-or-owner/repo#N> --body-file <path>
                                   [--dry-run] [--label cra-reviewed]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys


def parse_target(s: str) -> tuple[str, str, int]:
    m = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$", s)
    if m:
        return m.group(1), m.group(2), int(m.group(3))
    m = re.match(r"^([^/]+)/([^/#]+)#(\d+)$", s)
    if m:
        return m.group(1), m.group(2), int(m.group(3))
    raise SystemExit(f"Could not parse PR target: {s!r}")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), text=True, capture_output=True, check=check)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("target")
    p.add_argument("--body-file", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--label", default=None,
                   help="optional label to apply (e.g. cra-reviewed)")
    args = p.parse_args()

    owner, repo, n = parse_target(args.target)
    with open(args.body_file) as f:
        body = f.read()

    if args.dry_run:
        print(f"--- DRY RUN: would post to {owner}/{repo}#{n} ---")
        print(body)
        return

    res = run("gh", "pr", "comment", str(n),
              "--repo", f"{owner}/{repo}",
              "--body", body)
    print(res.stdout.strip())

    if args.label:
        run("gh", "pr", "edit", str(n),
            "--repo", f"{owner}/{repo}",
            "--add-label", args.label, check=False)


if __name__ == "__main__":
    main()
