"""Build the review-context bundle for a code review.

Four input modes:
  prep.py <pr-url>                # https://github.com/owner/repo/pull/N — review a PR
  prep.py <owner>/<repo>#<N>      # same, shorthand
  prep.py <N>                     # bare PR number — uses current repo
  prep.py --local [--base <ref>]   # branch HEAD vs base (default: origin/main or upstream)
  prep.py --uncommitted            # working tree + staged vs HEAD (everything dirty)
  prep.py --staged                 # staged index vs HEAD only
  prep.py --unstaged               # working tree vs HEAD only

Outputs JSON on stdout. The shape is the same regardless of mode — Claude Code
just sees a bundle with diff + context_files + (sometimes) PR metadata.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CACHE_ROOT = Path(os.environ.get("CRA_CACHE", str(Path.home() / ".cache" / "cra")))


def run(*args: str, cwd: str | None = None, check: bool = True) -> str:
    res = subprocess.run(list(args), cwd=cwd, text=True, capture_output=True, check=check)
    return res.stdout.strip()


def parse_target(s: str) -> tuple[str, str, int]:
    """Return (owner, repo, pr_number) from a URL, owner/repo#N, or bare N."""
    m = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$", s)
    if m:
        return m.group(1), m.group(2), int(m.group(3))
    m = re.match(r"^([^/]+)/([^/#]+)#(\d+)$", s)
    if m:
        return m.group(1), m.group(2), int(m.group(3))
    if s.isdigit():
        # use the current repo
        out = run("gh", "repo", "view", "--json", "owner,name")
        info = json.loads(out)
        return info["owner"]["login"], info["name"], int(s)
    raise SystemExit(f"Could not parse PR target: {s!r}")


def ensure_checkout(owner: str, repo: str, head_sha: str) -> Path:
    """Clone or fetch the repo into the cache, check out the head SHA."""
    cache = CACHE_ROOT / f"{owner}__{repo}"
    cache.mkdir(parents=True, exist_ok=True)
    if not (cache / ".git").exists():
        run("git", "clone", f"git@github.com:{owner}/{repo}.git", str(cache))
    run("git", "fetch", "origin", head_sha, cwd=str(cache), check=False)
    run("git", "fetch", "origin", cwd=str(cache), check=False)
    run("git", "checkout", "-f", head_sha, cwd=str(cache))
    return cache


def read_if(path: Path, max_bytes: int = 32_000) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) > max_bytes:
        return data[:max_bytes].decode("utf-8", errors="replace") + "\n…(truncated)\n"
    return data.decode("utf-8", errors="replace")


def gather_context_files(root: Path) -> dict[str, str]:
    """Load README.md, .codereview/rules.md, .greptile/rules.md, .cra/rules.md if present."""
    out: dict[str, str] = {}
    for relpath in ("README.md", ".codereview/rules.md", ".greptile/rules.md", ".cra/rules.md"):
        c = read_if(root / relpath)
        if c is not None:
            out[relpath] = c
    return out


def detect_default_base(cwd: Path) -> str:
    """Pick a sensible base ref for `--local` mode."""
    # Prefer the upstream of the current branch if set.
    try:
        upstream = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "--abbrev-ref", "@{upstream}"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        if upstream:
            return upstream
    except subprocess.CalledProcessError:
        pass
    # Else try origin/main, origin/master, main, master.
    for ref in ("origin/main", "origin/master", "main", "master"):
        try:
            subprocess.check_output(
                ["git", "-C", str(cwd), "rev-parse", "--verify", "--quiet", ref],
                stderr=subprocess.DEVNULL,
            )
            return ref
        except subprocess.CalledProcessError:
            continue
    raise SystemExit("Could not determine a base ref. Pass --base <ref> explicitly.")


def changed_files_from_diff(diff: str) -> list[dict]:
    """Parse a unified diff and return [{path, status}] entries.

    'status' is one of: added, deleted, modified, renamed.
    """
    files: list[dict] = []
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            # diff --git a/foo b/bar
            m = re.match(r"diff --git a/(.+?) b/(.+)$", line)
            if not m:
                continue
            a, b = m.group(1), m.group(2)
            path = b if b else a
            files.append({"path": path, "_a": a, "_b": b, "status": "modified"})
        elif line.startswith("new file mode") and files:
            files[-1]["status"] = "added"
        elif line.startswith("deleted file mode") and files:
            files[-1]["status"] = "deleted"
        elif line.startswith("rename from") and files:
            files[-1]["status"] = "renamed"
    # Strip internal fields
    for f in files:
        f.pop("_a", None)
        f.pop("_b", None)
    return files


def build_local_bundle(mode: str, base: str | None) -> dict:
    """Build a bundle for --local / --uncommitted / --staged / --unstaged modes."""
    cwd = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())

    if mode == "local":
        base_ref = base or detect_default_base(cwd)
        head_sha = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"], text=True).strip()
        base_sha = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", base_ref], text=True).strip()
        # Use merge-base so we describe only what this branch changed
        merge_base = subprocess.check_output(
            ["git", "-C", str(cwd), "merge-base", base_sha, head_sha], text=True).strip()
        diff = subprocess.check_output(
            ["git", "-C", str(cwd), "diff", "--no-color", f"{merge_base}..{head_sha}"], text=True)
        head_branch = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        title = f"[local] {head_branch} vs {base_ref}"
        body_lines = [f"Local diff between `{head_branch}` ({head_sha[:7]}) and `{base_ref}` (merge-base {merge_base[:7]})."]
        commits = subprocess.check_output(
            ["git", "-C", str(cwd), "log", "--oneline", "--no-decorate", f"{merge_base}..{head_sha}"],
            text=True,
        ).strip()
        if commits:
            body_lines.append("\nCommits on this branch (newest first):\n```\n" + commits + "\n```")
        body = "\n".join(body_lines)
        compare_base = base_ref
        compare_head = head_sha[:12]
    elif mode == "uncommitted":
        head_sha = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"], text=True).strip()
        # All changes since HEAD: working tree + staged
        diff = subprocess.check_output(
            ["git", "-C", str(cwd), "diff", "--no-color", "HEAD"], text=True)
        # If diff is empty, also check for untracked files
        if not diff.strip():
            untracked = subprocess.check_output(
                ["git", "-C", str(cwd), "ls-files", "--others", "--exclude-standard"], text=True).strip()
            if untracked:
                diff = f"# Untracked files (not yet added to git):\n# " + "\n# ".join(untracked.splitlines())
        title = f"[uncommitted] working-tree changes vs HEAD"
        body = f"Uncommitted local changes against `HEAD` ({head_sha[:7]}). Includes staged and unstaged."
        base_sha = head_sha
        compare_base = "HEAD"
        compare_head = "working-tree"
    elif mode == "staged":
        head_sha = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"], text=True).strip()
        diff = subprocess.check_output(
            ["git", "-C", str(cwd), "diff", "--no-color", "--cached"], text=True)
        title = f"[staged] index vs HEAD"
        body = f"Staged changes against `HEAD` ({head_sha[:7]}). About to be committed."
        base_sha = head_sha
        compare_base = "HEAD"
        compare_head = "INDEX"
    elif mode == "unstaged":
        head_sha = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"], text=True).strip()
        diff = subprocess.check_output(
            ["git", "-C", str(cwd), "diff", "--no-color"], text=True)
        title = f"[unstaged] working-tree vs index"
        body = f"Unstaged working-tree changes against the index. Base HEAD: {head_sha[:7]}."
        base_sha = head_sha
        compare_base = "INDEX"
        compare_head = "working-tree"
    else:
        raise SystemExit(f"unknown mode: {mode}")

    return {
        "mode": mode,
        "pr_ref": None,
        "pr_url": None,
        "pr_number": None,
        "owner": None,
        "repo": None,
        "state": None,
        "is_draft": None,
        "pr_title": title,
        "pr_body": body,
        "pr_author": subprocess.check_output(["git", "config", "user.name"], text=True).strip() or "",
        "head_sha": head_sha if mode != "local" else head_sha,
        "head_branch": compare_head,
        "base_sha": base_sha,
        "base_branch": compare_base,
        "checkout_path": str(cwd),
        "changed_files": changed_files_from_diff(diff),
        "stats": {
            "additions": sum(1 for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")),
            "deletions": sum(1 for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---")),
        },
        "diff": diff,
        "context_files": gather_context_files(cwd),
    }


def build_pr_bundle(target: str) -> dict:
    owner, repo, n = parse_target(target)
    pr_ref = f"{owner}/{repo}#{n}"

    pr_ref = f"{owner}/{repo}#{n}"
    pr_json_raw = run(
        "gh", "pr", "view", str(n),
        "--repo", f"{owner}/{repo}",
        "--json",
        "title,body,headRefName,headRefOid,baseRefName,baseRefOid,author,files,url,state,isDraft,additions,deletions",
    )
    pr = json.loads(pr_json_raw)

    diff = run("gh", "pr", "diff", str(n), "--repo", f"{owner}/{repo}")
    checkout = ensure_checkout(owner, repo, pr["headRefOid"])

    return {
        "mode": "pr",
        "pr_ref": pr_ref,
        "pr_url": pr["url"],
        "pr_number": n,
        "owner": owner,
        "repo": repo,
        "state": pr["state"],
        "is_draft": pr["isDraft"],
        "pr_title": pr["title"],
        "pr_body": pr["body"] or "",
        "pr_author": (pr["author"] or {}).get("login", ""),
        "head_sha": pr["headRefOid"],
        "head_branch": pr["headRefName"],
        "base_sha": pr["baseRefOid"],
        "base_branch": pr["baseRefName"],
        "checkout_path": str(checkout),
        "changed_files": [
            {"path": f["path"], "additions": f.get("additions", 0), "deletions": f.get("deletions", 0)}
            for f in pr["files"]
        ],
        "stats": {"additions": pr["additions"], "deletions": pr["deletions"]},
        "diff": diff,
        "context_files": gather_context_files(checkout),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("target", nargs="?", help="PR URL, owner/repo#N, or bare N (omit for local modes)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--local", action="store_true",
                      help="diff current branch HEAD against base (default: upstream or origin/main)")
    mode.add_argument("--uncommitted", action="store_true",
                      help="diff working tree + index against HEAD")
    mode.add_argument("--staged", action="store_true", help="diff index against HEAD")
    mode.add_argument("--unstaged", action="store_true", help="diff working tree against index")
    p.add_argument("--base", help="explicit base ref for --local (overrides auto-detect)")
    args = p.parse_args()

    if args.local:
        bundle = build_local_bundle("local", args.base)
    elif args.uncommitted:
        bundle = build_local_bundle("uncommitted", None)
    elif args.staged:
        bundle = build_local_bundle("staged", None)
    elif args.unstaged:
        bundle = build_local_bundle("unstaged", None)
    elif args.target:
        bundle = build_pr_bundle(args.target)
    else:
        p.error("must pass a PR target OR one of --local / --uncommitted / --staged / --unstaged")

    print(json.dumps(bundle, indent=2))


if __name__ == "__main__":
    main()
