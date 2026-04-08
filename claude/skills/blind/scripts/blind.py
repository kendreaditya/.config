#!/usr/bin/env python3
"""
blind.py — minimal Blind (teamblind.com) CLI

Read-only commands against the public Next.js RSC payloads. No login,
no cookies, no encryption. See plan in
~/.claude/plans/rustling-swimming-nygaard.md for the design.

Commands:
  search <query>           First page of search results
  read <url|alias>         Article comments + body excerpt
  feed [channel]           First page of a channel feed (or home)
  company <name>           First page of a company page
  export <url> [--format]  Dump article + comments to md or json

Common flags: --json, --limit N, -v

Future work / prior art:
  github.com/usrivastava92/teamblind-mcp — TypeScript MCP server that
  reverse-engineered the encrypted /api/* surface we sidestep here.
  It hardcodes Blind's RSA-2048 public key (src/config.ts) and uses
  Node `crypto.publicEncrypt` (PKCS#1) + SJCL AES-CCM to wrap requests.
  Allowlists 18 cookie-auth endpoints: /api/current-user(/company),
  /api/notifications, /api/jobs/*, /api/recent-channels(/add),
  /api/company/company-page-*, /api/ad-targeting/*, etc. Cookie comes
  from a `TEAMBLIND_COOKIE_HEADER` env var. If we ever want
  authenticated reads (notifications, jobs, profile, possibly private
  company channels) port their crypto into Python with `cryptography`
  + a small AES-CCM helper, plus a --cookie flag here. Writes
  (post/comment/vote/DM) are NOT in their allowlist — those go
  through Next.js Server Actions, which is a separate RE effort.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import gzip
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)
BASE = "https://www.teamblind.com"
RSC_TOKEN = "rbaxc"  # arbitrary; just needs to be present


class BlindError(Exception):
    pass


class BlindNotFound(BlindError):
    pass


def fetch_rsc(path: str, *, debug: bool = False) -> str:
    """Fetch a teamblind.com path as an RSC payload (text/x-component)."""
    if path.startswith("http"):
        # Caller passed a full URL — accept it.
        url = path
    else:
        url = BASE + path
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}_rsc={RSC_TOKEN}"
    headers = {
        "rsc": "1",
        "accept": "*/*",
        "user-agent": UA,
        "accept-encoding": "gzip",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as e:
        raise BlindError(f"HTTP {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise BlindError(f"network error for {url}: {e.reason}") from e
    raw = resp.read()
    if resp.headers.get("content-encoding") == "gzip":
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8", errors="replace")
    if debug:
        sys.stderr.write(f"[fetch] {url} -> {len(text)} bytes\n")
    return text


# ---------------------------------------------------------------------------
# RSC flight parser
# ---------------------------------------------------------------------------

# Each record begins at the start of a line with "<hex>:" followed by the
# value. Values may contain literal newlines (e.g. inside JSON strings),
# so do NOT split on \n. Use a regex that anchors at line starts.

_RECORD_START_RE = re.compile(r"^([0-9a-f]+):", re.MULTILINE)


def parse_records(text: str) -> dict[str, str]:
    """Split a flight payload into {record_id: raw_value_string}.

    The raw value is the text between this record's "id:" prefix and the
    next record's start (or EOF), with any trailing newline stripped.
    """
    records: dict[str, str] = {}
    starts = [(m.start(), m.group(1)) for m in _RECORD_START_RE.finditer(text)]
    for i, (start, rid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        val_start = start + len(rid) + 1  # skip "rid:"
        records[rid] = text[val_start:end].rstrip("\n")
    return records


def try_json(value: str) -> Any:
    """Parse a record value as JSON; return None if it isn't JSON."""
    if not value:
        return None
    if value[0] not in "[{":
        # Strings like "$Sreact.fragment" or component refs like I[...] are
        # not standard JSON; ignore for our purposes.
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def walk_objects(node: Any, depth: int = 0, max_depth: int = 60) -> Iterator[dict]:
    """Yield every dict found anywhere in a parsed JSON tree."""
    if depth > max_depth:
        return
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk_objects(v, depth + 1, max_depth)
    elif isinstance(node, list):
        for v in node:
            yield from walk_objects(v, depth + 1, max_depth)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class Post:
    alias: str
    title: str
    content: str  # may be truncated to 300 chars by Blind
    content_length: int  # full length per Blind's metadata
    author_nickname: str | None
    author_company: str | None
    channel_name: str | None
    created_at: str | None  # relative form, e.g. "4d", "Yesterday"
    written_at: str | None  # ISO 8601 absolute timestamp if present
    like_count: int
    comment_count: int
    view_count: int
    url: str

    @property
    def is_truncated(self) -> bool:
        return self.content_length > len(self.content)


@dataclass
class Comment:
    id: int
    parent_id: int
    author_nickname: str
    author_company: str | None
    content: str
    created_at: str | None
    written_at: str | None
    like_count: int
    is_op: bool
    replies: list["Comment"] = field(default_factory=list)


@dataclass
class Article:
    """A single article with its comments. Body may be excerpt-only."""

    alias: str
    title: str | None
    body: str | None  # may be a meta excerpt (~150 chars) for v1
    body_is_excerpt: bool
    author_nickname: str | None
    author_company: str | None
    channel_name: str | None
    url: str
    pinned: list[Comment] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    total_comment_count: int = 0


# ---------------------------------------------------------------------------
# Domain extractors
# ---------------------------------------------------------------------------


def _post_from_dict(d: dict) -> Post | None:
    """Build a Post from a Blind feed-listing object dict, if shaped right."""
    if d.get("articleType") not in ("post", "link"):
        return None
    if "title" not in d or "alias" not in d:
        return None
    return Post(
        alias=str(d.get("alias", "")),
        title=str(d.get("title", "") or ""),
        content=str(d.get("content", "") or ""),
        content_length=int(d.get("contentLength", 0) or 0),
        author_nickname=d.get("memberNickname"),
        author_company=d.get("memberCompanyName"),
        channel_name=(d.get("channelDetails") or {}).get("displayName")
        or d.get("boardName"),
        created_at=d.get("createdAt"),
        written_at=d.get("writedAt"),
        like_count=int(d.get("likeCnt", 0) or 0),
        comment_count=int(d.get("commentCnt", 0) or 0),
        view_count=int(d.get("viewCnt", 0) or 0),
        url=BASE + (d.get("scheme") or f"/article/{d.get('alias','')}"),
    )


def extract_post_list(text: str) -> list[Post]:
    """Find the main article list in a search/feed/channel/company page.

    Strategy: scan every record's parsed JSON tree, collect all candidate
    post objects, deduplicate by alias, and return them in document order.
    Sidebar widgets generally repeat the same posts as the main list, so
    deduplication is enough — we don't need a structural sidebar filter.
    """
    records = parse_records(text)
    seen: dict[str, Post] = {}
    order: list[str] = []
    for rid, raw in records.items():
        parsed = try_json(raw)
        if parsed is None:
            continue
        for obj in walk_objects(parsed):
            post = _post_from_dict(obj)
            if post is None:
                continue
            if post.alias in seen:
                continue
            seen[post.alias] = post
            order.append(post.alias)
    return [seen[a] for a in order]


def is_not_found(text: str) -> bool:
    """A page is a 404 when it has zero post-shaped objects AND a small body.

    Real Blind 404s come back as ~633 KB exact, all rendering the same
    NotFound boundary. The reliable signal is "no records have any post
    objects in them".
    """
    # Quick size heuristic: real Blind pages we care about are well over
    # 700 KB. 404s are stable at ~633 KB.
    if len(text) > 700_000:
        return False
    return not any(
        '"articleType"' in v for v in parse_records(text).values()
    )


def is_silent_fallback(text: str, expected_path: str) -> bool:
    """Detect when Blind silently redirects an unknown path to home.

    e.g. /topics/NonexistentChannel returns the home feed (HTTP 200)
    instead of a 404. Detected via og:url: real pages embed their
    canonical URL; the home fallback embeds the bare domain.
    """
    m = re.search(r'"property":"og:url","content":"([^"]+)"', text)
    if not m:
        return False
    og = m.group(1).rstrip("/")
    expected = expected_path.rstrip("/").lower()
    # If we asked for something specific (not "/") and og:url is just the
    # bare domain, this is the home fallback.
    if expected in ("", "/"):
        return False
    if og in ("https://www.teamblind.com", "http://www.teamblind.com"):
        return True
    return False


# --- single article extraction ---------------------------------------------


def _comment_from_dict(d: dict) -> Comment:
    replies = [
        _comment_from_dict(r) for r in (d.get("recomments") or []) if isinstance(r, dict)
    ]
    return Comment(
        id=int(d.get("id", 0) or 0),
        parent_id=int(d.get("parentCommentId", 0) or 0),
        author_nickname=str(d.get("memberNickname", "") or "anon"),
        author_company=d.get("companyName"),
        content=str(d.get("contentRaw") or d.get("content") or ""),
        created_at=d.get("createDate") or d.get("createdAt"),
        written_at=d.get("writedAt"),
        like_count=int(d.get("likeCnt", 0) or 0),
        is_op=bool(d.get("isOp")),
        replies=replies,
    )


def extract_article(text: str) -> Article:
    """Parse an /article/<alias> page into an Article + comments.

    The article body itself is lazy-loaded by Blind via a Server Action,
    so v1 falls back to the SEO meta description (truncated ~150 chars).
    Comments are present in full as JSON.
    """
    records = parse_records(text)

    title: str | None = None
    body_excerpt: str | None = None
    alias: str | None = None
    channel_name: str | None = None
    author_nickname: str | None = None
    author_company: str | None = None
    pinned: list[Comment] = []
    comments: list[Comment] = []
    total_count = 0

    for rid, raw in records.items():
        parsed = try_json(raw)
        if parsed is None:
            continue
        for obj in walk_objects(parsed):
            # Page <title> in App Router metadata is rendered as
            # ["$","title","0",{"children":"<title>"}]
            # which doesn't survive walk_objects (lists not dicts), so
            # we walk titles a different way below from the raw record.

            # initialData with commentList is the comment chunk
            if "commentList" in obj and isinstance(obj.get("commentList"), list):
                total_count = max(total_count, int(obj.get("totalCount", 0) or 0))
                for c in obj["commentList"]:
                    if isinstance(c, dict):
                        comments.append(_comment_from_dict(c))
                for c in obj.get("pinnedList") or []:
                    if isinstance(c, dict):
                        pinned.append(_comment_from_dict(c))

            # Article wrapper component props
            if "articleAlias" in obj:
                alias = alias or str(obj.get("articleAlias") or "")
                if obj.get("originalAuthorNickname"):
                    author_nickname = author_nickname or str(
                        obj["originalAuthorNickname"]
                    )
                ch = obj.get("channel")
                if isinstance(ch, dict):
                    channel_name = channel_name or (
                        ch.get("viewBoardName") or ch.get("boardName")
                    )

    # Pull title and body excerpt out of the page metadata records by raw
    # regex — they live in head <title> + <meta> elements that are encoded
    # as React element tuples (lists), not dicts.
    # Title:  ["$","title","0",{"children":"Article Title | Channel - Blind"}]
    title_match = re.search(
        r'\["?\$"?,"title","\d+",\s*\{"children":"([^"]+)"', text
    )
    if title_match:
        raw_title = html.unescape(title_match.group(1))
        # Strip the "| Channel - Blind" suffix
        title = re.sub(r"\s*\|\s*[^|]+\s*-\s*Blind\s*$", "", raw_title)

    # Meta description holds the body excerpt
    desc_match = re.search(
        r'"name":"description","content":"([^"]+)"', text
    )
    if desc_match:
        body_excerpt = html.unescape(desc_match.group(1))

    if alias is None:
        alias = ""

    # Author company comes from one of the comment-page records too — it's
    # encoded in the channel block, not always under originalAuthorNickname.
    # Leave None if absent; renderer handles it.

    return Article(
        alias=alias,
        title=title,
        body=body_excerpt,
        body_is_excerpt=True,
        author_nickname=author_nickname,
        author_company=author_company,
        channel_name=channel_name,
        url=f"{BASE}/article/{alias}" if alias else "",
        pinned=pinned,
        comments=comments,
        total_comment_count=total_count or len(comments),
    )


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def alias_from_url(url_or_alias: str) -> str:
    """Accept a full Blind URL or a bare alias and return just the alias."""
    s = url_or_alias.strip()
    if "://" in s or s.startswith("/"):
        # Try /article/<alias>, /post/<alias>, or .../posts/<slug>
        m = re.search(r"/(?:article|post|posts)/([^/?#]+)", s)
        if m:
            return m.group(1)
        # Last path segment fallback
        path = urllib.parse.urlparse(s).path
        seg = path.rstrip("/").split("/")[-1]
        return seg
    return s


def channel_url(name: str) -> str:
    """Map a channel name to its URL.

    Blind has both /channels/<name> (canonical) and /topics/<Name>. Try
    /topics/<name> with original casing — it works case-insensitively in
    our probes, so passing through user input as-is is fine.
    """
    # If the user passed a path-like value, use it directly
    if name.startswith("/"):
        return name
    return f"/topics/{name}"


# ---------------------------------------------------------------------------
# --since parsing and filtering
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([smhdw])\s*$")


def parse_duration(s: str) -> dt.timedelta:
    m = _DURATION_RE.match(s.lower())
    if not m:
        raise argparse.ArgumentTypeError(
            f"bad duration {s!r} (use e.g. 10m, 6h, 2d, 1w)"
        )
    n = int(m.group(1))
    unit = m.group(2)
    return dt.timedelta(
        seconds=n
        * {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 7 * 86400}[unit]
    )


def filter_since(posts: list[Post], delta: dt.timedelta) -> tuple[list[Post], bool]:
    """Filter posts to those written within `delta`.

    Returns (filtered, possibly_truncated). The truncation flag is True
    if every returned post is inside the window — meaning we may have
    silently dropped older-than-window posts but not seen the boundary,
    so there could be more in the window past the first page.
    """
    cutoff = dt.datetime.now(dt.timezone.utc) - delta
    out: list[Post] = []
    saw_older = False
    for p in posts:
        ts = _parse_ts(p.written_at)
        if ts is None:
            # Without an absolute timestamp we can't filter; keep it.
            out.append(p)
            continue
        if ts >= cutoff:
            out.append(p)
        else:
            saw_older = True
    truncated = bool(out) and not saw_older
    return out, truncated


def _parse_ts(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        # Blind uses "2026-04-03T22:00:00.000Z"
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=dt.timezone.utc
        )
    except ValueError:
        try:
            return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _wrap(text: str, width: int = 80, indent: str = "") -> str:
    out_lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            out_lines.append("")
            continue
        words = paragraph.split()
        line = indent
        for w in words:
            if len(line) + len(w) + 1 > width and line.strip():
                out_lines.append(line.rstrip())
                line = indent + w + " "
            else:
                line += w + " "
        if line.strip():
            out_lines.append(line.rstrip())
    return "\n".join(out_lines)


def render_post_listing(posts: list[Post], limit: int | None = None) -> str:
    if limit is not None:
        posts = posts[:limit]
    if not posts:
        return "(no results)"
    lines = []
    for i, p in enumerate(posts, 1):
        head = f"{i:>3}. {p.title}"
        meta_bits = []
        if p.author_company:
            meta_bits.append(p.author_company)
        if p.author_nickname:
            meta_bits.append(f"@{p.author_nickname}")
        if p.created_at:
            meta_bits.append(p.created_at)
        meta_bits.append(f"♥{p.like_count}")
        meta_bits.append(f"💬{p.comment_count}")
        meta_bits.append(f"👁{p.view_count}")
        meta = "  ·  ".join(meta_bits)

        snippet = p.content.strip().replace("\n", " ")
        if p.is_truncated:
            snippet += f" […+{p.content_length - len(p.content)} chars]"

        lines.append(head)
        lines.append(f"     {meta}")
        if snippet:
            lines.append(_wrap(snippet, width=78, indent="     "))
        lines.append(f"     {p.url}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _render_comment(c: Comment, depth: int = 0) -> str:
    indent = "  " * depth
    bullet = "└─" if depth > 0 else "•"
    who_bits = [c.author_nickname]
    if c.author_company:
        who_bits.append(f"({c.author_company})")
    if c.is_op:
        who_bits.append("[OP]")
    if c.created_at:
        who_bits.append(f"· {c.created_at}")
    who_bits.append(f"· ♥{c.like_count}")
    head = f"{indent}{bullet} {' '.join(who_bits)}"
    body = _wrap(c.content, width=78 - len(indent) - 4, indent=indent + "    ")
    out = [head, body]
    for r in c.replies:
        out.append(_render_comment(r, depth + 1))
    return "\n".join(out)


def render_article(a: Article) -> str:
    lines = []
    lines.append(f"# {a.title or '(untitled)'}")
    meta_bits = []
    if a.channel_name:
        meta_bits.append(a.channel_name)
    if a.author_nickname:
        meta_bits.append(f"@{a.author_nickname}")
    if a.author_company:
        meta_bits.append(a.author_company)
    if meta_bits:
        lines.append("  ·  ".join(meta_bits))
    lines.append(a.url)
    lines.append("")
    if a.body:
        lines.append(_wrap(a.body, width=78))
        if a.body_is_excerpt:
            lines.append("")
            lines.append(
                "  ⚠ Body shown is the SEO excerpt (~150 chars). Blind lazy-"
            )
            lines.append(
                "    loads the full article body via a Server Action which is"
            )
            lines.append(
                "    out of scope for v1. Open the URL above for the full text."
            )
    lines.append("")
    lines.append(f"── Comments ({a.total_comment_count}) ──")
    lines.append("")
    if a.pinned:
        lines.append("📌 Pinned:")
        for c in a.pinned:
            lines.append(_render_comment(c))
            lines.append("")
    for c in a.comments:
        lines.append(_render_comment(c))
        lines.append("")
    return "\n".join(lines).rstrip()


def render_markdown(a: Article) -> str:
    out = []
    out.append(f"# {a.title or '(untitled)'}")
    meta_bits = []
    if a.channel_name:
        meta_bits.append(f"*{a.channel_name}*")
    if a.author_nickname:
        meta_bits.append(f"**@{a.author_nickname}**")
    if a.author_company:
        meta_bits.append(a.author_company)
    if meta_bits:
        out.append(" · ".join(meta_bits) + f" · [source]({a.url})")
    out.append("")
    if a.body:
        out.append(a.body)
        if a.body_is_excerpt:
            out.append("")
            out.append("> *Body excerpted (~150 chars). Full body lazy-loaded by Blind.*")
    out.append("")
    out.append(f"## Comments ({a.total_comment_count})")
    out.append("")
    if a.pinned:
        out.append("### 📌 Pinned")
        out.append("")
        for c in a.pinned:
            out.append(_md_comment(c))
        out.append("")
    for c in a.comments:
        out.append(_md_comment(c))
    return "\n".join(out)


def _md_comment(c: Comment, depth: int = 0) -> str:
    indent = "  " * depth
    op_tag = " **[OP]**" if c.is_op else ""
    company = f" ({c.author_company})" if c.author_company else ""
    when = f" · {c.created_at}" if c.created_at else ""
    head = (
        f"{indent}- **@{c.author_nickname}**{company}{op_tag}{when} · ♥{c.like_count}"
    )
    body_lines = [f"{indent}  {ln}" for ln in c.content.split("\n")]
    parts = [head] + body_lines
    for r in c.replies:
        parts.append(_md_comment(r, depth + 1))
    return "\n".join(parts)


def to_jsonable(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj):
        return {k: to_jsonable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_search(args: argparse.Namespace) -> int:
    q = urllib.parse.quote(args.query)
    text = fetch_rsc(f"/search/{q}", debug=args.verbose)
    if is_not_found(text):
        raise BlindNotFound(f"no search results page for {args.query!r}")
    posts = extract_post_list(text)
    if args.json:
        print(json.dumps([to_jsonable(p) for p in posts[: args.limit or len(posts)]], indent=2))
    else:
        print(render_post_listing(posts, limit=args.limit))
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    alias = alias_from_url(args.url)
    if not alias:
        raise BlindError(f"could not parse alias from {args.url!r}")
    path = f"/article/{alias}"
    text = fetch_rsc(path, debug=args.verbose)
    if is_not_found(text):
        raise BlindNotFound(f"no such article: {alias}")
    article = extract_article(text)
    if args.json:
        print(json.dumps(to_jsonable(article), indent=2))
    else:
        print(render_article(article))
    return 0


def cmd_feed(args: argparse.Namespace) -> int:
    if args.channel:
        path = channel_url(args.channel)
        label = args.channel
    else:
        path = "/"
        label = "home"
    text = fetch_rsc(path, debug=args.verbose)
    if is_not_found(text):
        raise BlindNotFound(f"no such channel: {label}")
    if args.channel and is_silent_fallback(text, path):
        raise BlindNotFound(
            f"no such channel: {label} "
            "(Blind silently redirects unknown topics to home)"
        )
    posts = extract_post_list(text)
    truncated = False
    if args.since:
        delta = parse_duration(args.since)
        posts, truncated = filter_since(posts, delta)
    if args.json:
        print(json.dumps([to_jsonable(p) for p in posts[: args.limit or len(posts)]], indent=2))
    else:
        print(render_post_listing(posts, limit=args.limit))
        if truncated:
            sys.stderr.write(
                "\n⚠ All returned posts fall inside --since window; there may be\n"
                "  more posts in this window beyond the first page (pagination\n"
                "  is not supported in v1).\n"
            )
    return 0


def cmd_company(args: argparse.Namespace) -> int:
    path = f"/company/{args.name}"
    text = fetch_rsc(path, debug=args.verbose)
    if is_not_found(text):
        raise BlindNotFound(f"no such company page: {args.name}")
    if is_silent_fallback(text, path):
        raise BlindNotFound(f"no such company page: {args.name}")
    posts = extract_post_list(text)
    truncated = False
    if args.since:
        delta = parse_duration(args.since)
        posts, truncated = filter_since(posts, delta)
    if args.json:
        print(json.dumps([to_jsonable(p) for p in posts[: args.limit or len(posts)]], indent=2))
    else:
        print(render_post_listing(posts, limit=args.limit))
        if truncated:
            sys.stderr.write(
                "\n⚠ All returned posts fall inside --since window (truncation possible).\n"
            )
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    alias = alias_from_url(args.url)
    if not alias:
        raise BlindError(f"could not parse alias from {args.url!r}")
    text = fetch_rsc(f"/article/{alias}", debug=args.verbose)
    if is_not_found(text):
        raise BlindNotFound(f"no such article: {alias}")
    article = extract_article(text)
    if args.format == "json":
        sys.stdout.write(json.dumps(to_jsonable(article), indent=2))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_markdown(article))
        sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    # Common flags shared by every subcommand
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="emit JSON instead of text")
    common.add_argument("--limit", type=int, default=None, help="cap number of results")
    common.add_argument("-v", "--verbose", action="store_true",
                        help="debug output to stderr")

    p = argparse.ArgumentParser(
        prog="blind",
        description="minimal Blind (teamblind.com) CLI — read-only, no auth",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", parents=[common], help="search Blind for posts")
    s.add_argument("query", help="search query")
    s.set_defaults(func=cmd_search)

    r = sub.add_parser("read", parents=[common],
                       help="read an article (body excerpt + comments)")
    r.add_argument("url", help="article URL or bare alias")
    # Note: ?sort=recent is silently ignored on /article/ pages — Blind
    # routes comment sorting through a Server Action, not a query param.
    # Topic-aggregation URLs (/company/<co>/posts/<slug>) honor it but
    # those aren't what `read` targets, so the flag would mislead.
    r.set_defaults(func=cmd_read)

    f = sub.add_parser("feed", parents=[common],
                       help="browse a channel feed (or home if no name)")
    f.add_argument("channel", nargs="?", default=None,
                   help="channel name, e.g. Layoffs (omit for home feed)")
    f.add_argument("--since", default=None,
                   help="filter to posts within this duration, e.g. 6h, 2d")
    f.set_defaults(func=cmd_feed)

    c = sub.add_parser("company", parents=[common], help="browse a company page")
    c.add_argument("name", help="company URL alias, e.g. Meta")
    c.add_argument("--since", default=None,
                   help="filter to posts within this duration")
    c.set_defaults(func=cmd_company)

    e = sub.add_parser("export", parents=[common],
                       help="dump an article to markdown or json")
    e.add_argument("url", help="article URL or alias")
    e.add_argument("--format", choices=["md", "json"], default="md")
    e.set_defaults(func=cmd_export)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BlindNotFound as e:
        sys.stderr.write(f"not found: {e}\n")
        return 2
    except BlindError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted\n")
        return 130


if __name__ == "__main__":
    sys.exit(main())
