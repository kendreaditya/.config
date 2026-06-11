#!/usr/bin/env python3
"""
reddit — minimal Reddit search & read CLI (read-only)

Reddit's public *.json endpoints (www/old/np/api/oauth/no-www) now return
HTTP 403 + an HTML block page for unauthenticated clients regardless of
User-Agent — a blanket block, not transient rate-limiting. This CLI works
around that with two backends, in preference order:

  1. OAuth (preferred, reliable) — userless "application-only" token flow
     against https://www.reddit.com/api/v1/access_token, then JSON from
     https://oauth.reddit.com/...  . Used automatically when these env vars
     are present (no values are ever printed):
         REDDIT_CLIENT_ID       (required)
         REDDIT_CLIENT_SECRET   (required)
         REDDIT_USERNAME        (optional — enables the password grant)
         REDDIT_PASSWORD        (optional — enables the password grant)
     With username+password it uses the `password` grant; otherwise it uses
     the `client_credentials` (installed/userless) grant. Both return real
     Reddit JSON. To register an app: https://www.reddit.com/prefs/apps
     → "create another app" → type "script" → note the client id (under the
     app name) and secret. See the reddit SKILL.md for the full walkthrough.

  2. Redlib (fallback, flaky) — public open-source Reddit frontends. Redlib
     renders HTML (it does NOT expose Reddit's .json API), so this backend
     scrapes the page. Instance availability is unreliable: we keep a list
     of instances and rotate to the next on any failure. Some instances are
     up but rate-limited, behind an anti-bot interstitial, or geo-blocked,
     so a fetch may have to try several before one answers. Set REDLIB_HOST
     to pin a single instance.

Commands:
  search <query>                 Search across Reddit
  subreddit <name>               Browse a subreddit listing (hot/new/top/...)
  comments <post-url-or-id>      A post + its comment tree
  user <name>                    A user's recent posts + comments

Common flags: --json, --limit N, -v/--verbose, plus --sort / --time where
relevant. Exit codes: 0 ok, 1 error, 2 not-found.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

UA = "claude-reddit-skill/2.0 (read-only; +https://github.com/redlib-org)"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)

# Redlib instances to rotate through. Availability is flaky — the fetcher
# tries each in order until one returns a usable page. A working instance
# found during development is listed first; the rest are fallbacks. Override
# with REDLIB_HOST=https://my.instance to pin one.
REDLIB_INSTANCES = [
    "https://redlib.perennialte.ch",
    "https://safereddit.com",
    "https://redlib.catsarch.com",
    "https://redlib.r4fo.com",
    "https://reddit.nerdvpn.de",
    "https://redlib.freedit.eu",
    "https://redlib.nadeko.net",
    "https://redlib.tiekoetter.com",
    "https://redlib.privacydev.net",
    "https://l.opnxng.com",
    "https://redlib.ducks.party",
    "https://red.ngn.tf",
    "https://libreddit.kavin.rocks",
]

_verbose = False


def _log(msg: str) -> None:
    if _verbose:
        print(f"[reddit] {msg}", file=sys.stderr)


class RedditError(Exception):
    pass


class RedditNotFound(RedditError):
    pass


# ---------------------------------------------------------------------------
# Data classes (backend-agnostic schema)
# ---------------------------------------------------------------------------


@dataclass
class Post:
    id: str
    title: str
    subreddit: str
    author: str
    score: int
    num_comments: int
    created_utc: str  # ISO 8601 (empty if unknown)
    url: str          # the link target (external for link posts)
    permalink: str    # absolute reddit.com permalink
    selftext: str     # post body (may be truncated/empty)
    is_self: bool


@dataclass
class Comment:
    author: str
    score: int
    created_utc: str
    body: str
    depth: int
    replies: list["Comment"] = field(default_factory=list)


@dataclass
class Thread:
    post: Post
    comments: list[Comment]
    total_comment_count: int


@dataclass
class UserItem:
    kind: str  # "post" or "comment"
    title: str  # post title, or "comment in r/x" for comments
    subreddit: str
    score: int
    created_utc: str
    permalink: str
    body: str  # selftext for posts, comment body for comments


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


def _http(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict | None = None,
    timeout: int = 20,
) -> tuple[int, str, bytes]:
    """Return (status, content_type, body). Raises RedditError on transport
    failure; HTTP error *codes* are returned (not raised) so callers can
    decide whether to rotate/fall back."""
    hdrs = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, r.headers.get("content-type", ""), body
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type", "") if e.headers else "", e.read()[:2000]
    except urllib.error.URLError as e:
        raise RedditError(f"network error for {url}: {e.reason}") from e
    except TimeoutError as e:
        raise RedditError(f"timeout for {url}") from e


def _looks_like_json(ctype: str, body: bytes) -> bool:
    if body[:1] not in (b"{", b"["):
        return False
    try:
        json.loads(body)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------


def _have_oauth_creds() -> bool:
    return bool(os.environ.get("REDDIT_CLIENT_ID")) and bool(
        os.environ.get("REDDIT_CLIENT_SECRET")
    )


# ---------------------------------------------------------------------------
# OAuth backend
# ---------------------------------------------------------------------------

import base64

_OAUTH_TOKEN: str | None = None


def _oauth_token() -> str:
    """Fetch (and cache for the process) an OAuth bearer token. Uses the
    password grant if REDDIT_USERNAME/PASSWORD are set, else the userless
    client_credentials grant. Never logs secret values."""
    global _OAUTH_TOKEN
    if _OAUTH_TOKEN:
        return _OAUTH_TOKEN
    cid = os.environ["REDDIT_CLIENT_ID"]
    secret = os.environ["REDDIT_CLIENT_SECRET"]
    user = os.environ.get("REDDIT_USERNAME")
    pw = os.environ.get("REDDIT_PASSWORD")
    if user and pw:
        form = {"grant_type": "password", "username": user, "password": pw}
        _log("oauth: password grant")
    else:
        # Installed/userless application-only token.
        form = {"grant_type": "https://oauth.reddit.com/grants/installed_client",
                "device_id": "DO_NOT_TRACK_THIS_DEVICE"}
        _log("oauth: client_credentials (userless) grant")
    data = urllib.parse.urlencode(form).encode()
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    status, ctype, body = _http(
        "https://www.reddit.com/api/v1/access_token",
        data=data,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": UA,
        },
    )
    if status != 200:
        raise RedditError(
            f"OAuth token request failed (HTTP {status}). Check REDDIT_CLIENT_ID/"
            "REDDIT_CLIENT_SECRET (and USERNAME/PASSWORD if set). "
            "App type must be 'script' or 'installed'."
        )
    try:
        tok = json.loads(body)["access_token"]
    except Exception as e:
        raise RedditError(f"OAuth token response had no access_token: {e}") from e
    _OAUTH_TOKEN = tok
    return tok


def _oauth_get(path: str, params: dict | None = None) -> Any:
    """GET a JSON resource from oauth.reddit.com."""
    tok = _oauth_token()
    url = "https://oauth.reddit.com" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    _log(f"GET {url}")
    status, ctype, body = _http(
        url, headers={"Authorization": f"Bearer {tok}", "User-Agent": UA}
    )
    if status == 404:
        raise RedditNotFound(f"not found: {path}")
    if status != 200:
        raise RedditError(f"HTTP {status} from oauth.reddit.com for {path}")
    try:
        return json.loads(body)
    except Exception as e:
        raise RedditError(f"non-JSON from oauth.reddit.com for {path}: {e}") from e


def _iso(ts: Any) -> str:
    try:
        return dt.datetime.fromtimestamp(int(float(ts)), dt.timezone.utc).isoformat()
    except Exception:
        return ""


def _post_from_listing(d: dict) -> Post:
    pid = str(d.get("id") or d.get("name") or "")
    perm = d.get("permalink") or ""
    return Post(
        id=pid,
        title=html.unescape(str(d.get("title") or "")),
        subreddit=str(d.get("subreddit") or ""),
        author=str(d.get("author") or ""),
        score=int(d.get("score") or 0),
        num_comments=int(d.get("num_comments") or 0),
        created_utc=_iso(d.get("created_utc")),
        url=str(d.get("url") or (f"https://reddit.com{perm}" if perm else "")),
        permalink=f"https://reddit.com{perm}" if perm else "",
        selftext=html.unescape(str(d.get("selftext") or "")),
        is_self=bool(d.get("is_self")),
    )


def _oauth_search(query: str, sort: str, time_filter: str, limit: int,
                  subreddit: str | None = None) -> list[Post]:
    params = {"q": query, "sort": sort, "t": time_filter, "limit": limit,
              "raw_json": 1}
    if subreddit:
        params["restrict_sr"] = "on"
        path = f"/r/{subreddit}/search"
    else:
        path = "/search"
    data = _oauth_get(path, params)
    children = (data.get("data") or {}).get("children") or []
    return [_post_from_listing(c["data"]) for c in children if c.get("kind") == "t3"]


def _oauth_subreddit(name: str, sort: str, time_filter: str, limit: int) -> list[Post]:
    params = {"limit": limit, "raw_json": 1}
    if sort == "top":
        params["t"] = time_filter
    data = _oauth_get(f"/r/{name}/{sort}", params)
    children = (data.get("data") or {}).get("children") or []
    return [_post_from_listing(c["data"]) for c in children if c.get("kind") == "t3"]


def _oauth_comment_tree(node: dict, depth: int = 0) -> Comment | None:
    if node.get("kind") != "t1":
        return None
    d = node.get("data") or {}
    replies_obj = d.get("replies")
    kids: list[Comment] = []
    if isinstance(replies_obj, dict):
        for ch in (replies_obj.get("data") or {}).get("children") or []:
            c = _oauth_comment_tree(ch, depth + 1)
            if c:
                kids.append(c)
    return Comment(
        author=str(d.get("author") or "[deleted]"),
        score=int(d.get("score") or 0),
        created_utc=_iso(d.get("created_utc")),
        body=html.unescape(str(d.get("body") or "")),
        depth=depth,
        replies=kids,
    )


def _oauth_comments(subreddit: str, post_id: str, sort: str, limit: int) -> Thread:
    data = _oauth_get(
        f"/r/{subreddit}/comments/{post_id}",
        {"sort": sort, "limit": limit, "raw_json": 1},
    )
    if not isinstance(data, list) or len(data) < 2:
        raise RedditNotFound(f"no such post: {post_id}")
    post_children = (data[0].get("data") or {}).get("children") or []
    if not post_children:
        raise RedditNotFound(f"no such post: {post_id}")
    post = _post_from_listing(post_children[0]["data"])
    comments: list[Comment] = []
    for ch in (data[1].get("data") or {}).get("children") or []:
        c = _oauth_comment_tree(ch)
        if c:
            comments.append(c)
    return Thread(post=post, comments=comments, total_comment_count=post.num_comments)


def _oauth_user(name: str, limit: int) -> list[UserItem]:
    data = _oauth_get(f"/user/{name}/overview", {"limit": limit, "raw_json": 1})
    children = (data.get("data") or {}).get("children") or []
    items: list[UserItem] = []
    for c in children:
        d = c.get("data") or {}
        perm = d.get("permalink") or ""
        if c.get("kind") == "t3":
            items.append(UserItem(
                kind="post",
                title=html.unescape(str(d.get("title") or "")),
                subreddit=str(d.get("subreddit") or ""),
                score=int(d.get("score") or 0),
                created_utc=_iso(d.get("created_utc")),
                permalink=f"https://reddit.com{perm}" if perm else "",
                body=html.unescape(str(d.get("selftext") or ""))[:500],
            ))
        elif c.get("kind") == "t1":
            items.append(UserItem(
                kind="comment",
                title=f"comment in r/{d.get('subreddit','')}",
                subreddit=str(d.get("subreddit") or ""),
                score=int(d.get("score") or 0),
                created_utc=_iso(d.get("created_utc")),
                permalink=f"https://reddit.com{perm}" if perm else "",
                body=html.unescape(str(d.get("body") or "")),
            ))
    return items


# ---------------------------------------------------------------------------
# Redlib (HTML-scraping) backend
# ---------------------------------------------------------------------------


def _redlib_hosts() -> list[str]:
    pinned = os.environ.get("REDLIB_HOST")
    if pinned:
        return [pinned.rstrip("/")]
    return [h.rstrip("/") for h in REDLIB_INSTANCES]


# Status codes worth one short retry on the SAME instance before rotating —
# a busy/rate-limited instance often recovers within a second or two, and the
# good instance is too scarce to abandon on the first hiccup.
_TRANSIENT = {429, 500, 502, 503, 504, 520, 521, 522, 523, 524}


def _redlib_fetch(path: str, *, not_found_label: str | None = None) -> str:
    """Fetch a Redlib HTML page, rotating instances until one serves a real
    Redlib page (not a 403/interstitial/placeholder). Returns the HTML.

    If `not_found_label` is set, a reachable instance returning HTTP 404 (the
    resource genuinely does not exist on Reddit) raises RedditNotFound rather
    than being treated as a transport failure to rotate past."""
    last_err = None
    saw_404 = False
    for host in _redlib_hosts():
        url = host + path
        status = None
        body = b""
        for attempt in range(2):  # one retry on transient failures
            _log(f"redlib try {url}" + (f" (retry {attempt})" if attempt else ""))
            try:
                status, ctype, body = _http(
                    url,
                    headers={"User-Agent": BROWSER_UA, "Accept": "text/html"},
                    timeout=15,
                )
            except RedditError as e:
                last_err = str(e)
                _log(f"  -> {e}")
                status = None
                if attempt == 0:
                    time.sleep(1.5)
                    continue
                break
            if status == 200 or status not in _TRANSIENT:
                break
            last_err = f"HTTP {status} from {host}"
            _log(f"  -> HTTP {status} (transient)")
            if attempt == 0:
                time.sleep(1.5)
        if status != 200:
            if status == 404:
                saw_404 = True
            if status is not None:
                last_err = f"HTTP {status} from {host}"
                _log(f"  -> HTTP {status}")
            continue
        text = body.decode("utf-8", "replace")
        low = text[:800].lower()
        if "making sure you" in low or "just a moment" in low or "checking your browser" in low:
            last_err = f"{host} served an anti-bot interstitial"
            _log("  -> interstitial")
            continue
        # A real Redlib content page has post/comment/listing markup.
        if ('class="post"' in text or 'class="post ' in text
                or 'class="comment"' in text or 'id="commentQueryForms"' in text
                or 'class="post_error"' in text):
            _log(f"  -> ok ({len(text)} bytes) via {host}")
            return text
        last_err = f"{host} returned HTML without Redlib markup (size {len(text)})"
        _log(f"  -> no redlib markup")
    # If a reachable instance said 404 and the caller asked us to surface that
    # as not-found, do so (exit 2) instead of the generic flaky-instance error.
    if not_found_label and saw_404:
        raise RedditNotFound(not_found_label)
    raise RedditError(
        "all Redlib instances failed (this is expected — they are flaky). "
        f"last: {last_err}. Tip: set REDLIB_HOST=https://<instance> to pin one, "
        "or add REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET to use the reliable OAuth "
        "path (see the reddit SKILL.md)."
    )


# --- tiny HTML helpers ---

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)</p>", "\n\n", s)
    s = _TAG_RE.sub("", s)
    s = html.unescape(s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _attr(block: str, attr: str) -> str:
    m = re.search(rf'{attr}="([^"]*)"', block)
    return html.unescape(m.group(1)) if m else ""


def _parse_count(raw: str) -> int:
    """Parse Redlib counts. Prefer the exact value in the title="N" attr;
    fall back to the visible text which may use k/m abbreviations."""
    raw = raw.strip().replace(",", "")
    if not raw or raw == "•":
        return 0
    m = re.match(r"(-?\d+(?:\.\d+)?)\s*([kmKM]?)", raw)
    if not m:
        return 0
    val = float(m.group(1))
    suf = m.group(2).lower()
    if suf == "k":
        val *= 1_000
    elif suf == "m":
        val *= 1_000_000
    return int(val)


def _redlib_created(block: str) -> str:
    """Redlib puts an absolute UTC time in the title= of the .created span:
    title="Jun 02 2026, 07:00:06 UTC". Convert to ISO 8601."""
    m = re.search(r'class="created"[^>]*title="([^"]+)"', block)
    if not m:
        return ""
    raw = m.group(1).replace(" UTC", "").strip()
    for fmt in ("%b %d %Y, %H:%M:%S", "%b %d %Y, %H:%M"):
        try:
            return dt.datetime.strptime(raw, fmt).replace(
                tzinfo=dt.timezone.utc).isoformat()
        except ValueError:
            continue
    return raw


# Split a listing page into individual post blocks.
_POST_SPLIT_RE = re.compile(r'<div class="post(?:\s[^"]*)?"\s+id="([a-z0-9]+)"', re.I)


def _redlib_posts(html_text: str, host: str) -> list[Post]:
    posts: list[Post] = []
    matches = list(_POST_SPLIT_RE.finditer(html_text))
    for i, m in enumerate(matches):
        pid = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html_text)
        block = html_text[start:end]
        # The canonical post link is the post_footer "post_comments" <a>, which
        # always carries /r/<sub>/comments/<id>/... and the exact comment count
        # in its title= attr. The post_title may also contain a "post_flair"
        # <a> pointing at a flair-search URL — never use that as the permalink.
        href = ""
        fm = re.search(r'class="post_comments"[^>]*href="([^"]+)"', block)
        if not fm:
            fm = re.search(r'href="([^"]+)"\s+class="post_comments"', block)
        if fm:
            href = fm.group(1)
        # title: pick the <a> inside post_title whose href is a /comments/ link
        # (i.e. not the flair link); fall back to the last <a> in the title.
        title = ""
        title_region = re.search(r'class="post_title">(.*?)</h2>', block, re.S)
        if title_region:
            anchors = re.findall(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>',
                                 title_region.group(1), re.S)
            for ahref, atext in anchors:
                if "/comments/" in ahref:
                    title = _strip_html(atext)
                    if not href:
                        href = ahref
                    break
            if not title and anchors:
                title = _strip_html(anchors[-1][1])
        if not title:
            continue
        sub_m = re.search(r'class="post_subreddit"[^>]*href="/r/([^"/]+)"', block)
        auth_m = re.search(r'class="post_author[^"]*"[^>]*href="/u(?:ser)?/([^"/]+)"', block)
        score_m = re.search(r'class="post_score"[^>]*title="([^"]*)"', block)
        if not score_m:
            score_m = re.search(r'class="post_score"[^>]*>\s*([0-9.,kmKM]+)', block)
        # external link target for link posts
        link_m = re.search(r'class="post_thumbnail[^"]*"\s+href="([^"]+)"', block)
        permalink = f"https://reddit.com{href}" if href.startswith("/") else href
        body_m = re.search(r'class="post_body[^"]*">(.*?)</div>\s*(?:<footer|<div class="post_footer|$)',
                           block, re.S)
        selftext = _strip_html(body_m.group(1)) if body_m else ""
        ext = link_m.group(1) if link_m else ""
        posts.append(Post(
            id=pid,
            title=title,
            subreddit=sub_m.group(1) if sub_m else "",
            author=auth_m.group(1) if auth_m else "",
            score=_parse_count(score_m.group(1)) if score_m else 0,
            num_comments=_redlib_comment_count(block),
            created_utc=_redlib_created(block),
            url=(ext if ext.startswith("http") else permalink),
            permalink=permalink,
            selftext=selftext,
            is_self=not bool(ext.startswith("http")),
        ))
    return posts


def _redlib_comment_count(block: str) -> int:
    # The post_footer link reads:  <a ... class="post_comments" title="13 comments">13 comments</a>
    m = re.search(r'class="post_comments"[^>]*title="([0-9.,kmKM]+)\s*comment', block, re.I)
    if m:
        return _parse_count(m.group(1))
    m = re.search(r'class="post_comments"[^>]*>\s*([0-9.,kmKM]+)\s*comment', block, re.I)
    return _parse_count(m.group(1)) if m else 0


def _redlib_search(query: str, sort: str, time_filter: str, limit: int,
                   subreddit: str | None) -> list[Post]:
    params = {"q": query, "sort": sort, "t": time_filter}
    if subreddit:
        path = f"/r/{subreddit}/search?" + urllib.parse.urlencode(params) + "&restrict_sr=on"
    else:
        path = "/search?" + urllib.parse.urlencode(params)
    html_text = _redlib_fetch(path)
    return _redlib_posts(html_text, "")[:limit]


def _redlib_subreddit(name: str, sort: str, time_filter: str, limit: int) -> list[Post]:
    if sort == "top":
        path = f"/r/{name}/top?t={time_filter}"
    elif sort in ("hot", "new", "rising", "controversial"):
        path = f"/r/{name}/{sort}"
    else:
        path = f"/r/{name}/{sort}"
    html_text = _redlib_fetch(path, not_found_label=f"no such subreddit: r/{name}")
    if 'class="post_error"' in html_text and 'class="post"' not in html_text:
        raise RedditNotFound(f"no such subreddit: r/{name}")
    return _redlib_posts(html_text, "")[:limit]


# Comment parsing: Redlib comments are <div id="xxx" class="comment"> with a
# nested <blockquote class="replies"> holding children. We parse by walking
# the markup and tracking nesting via the comment div positions.

_COMMENT_OPEN_RE = re.compile(r'<div id="[a-z0-9]+" class="comment">')


def _redlib_parse_comments(html_text: str, limit: int) -> list[Comment]:
    # Restrict to the thread region.
    tstart = html_text.find('<div class="thread">')
    region = html_text[tstart:] if tstart >= 0 else html_text

    # Build a list of (pos, is_open_comment, is_reply_open, is_reply_close)
    # then reconstruct nesting via a stack of depths.
    tokens = []
    for m in _COMMENT_OPEN_RE.finditer(region):
        tokens.append((m.start(), "comment", m.end()))
    for m in re.finditer(r'<blockquote class="replies">', region):
        tokens.append((m.start(), "open", m.end()))
    for m in re.finditer(r'</blockquote>', region):
        tokens.append((m.start(), "close", m.end()))
    tokens.sort(key=lambda t: t[0])

    roots: list[Comment] = []
    stack: list[Comment] = []  # current ancestry of comments
    depth = 0
    # We need each comment's block to extract fields: take text from this
    # comment's open to the next token.
    for i, (pos, kind, end) in enumerate(tokens):
        if kind == "open":
            depth += 1
        elif kind == "close":
            depth = max(0, depth - 1)
            if stack and len(stack) > depth:
                stack.pop()
        elif kind == "comment":
            nxt = tokens[i + 1][0] if i + 1 < len(tokens) else len(region)
            block = region[pos:nxt]
            c = _redlib_one_comment(block, depth)
            if c is None:
                continue
            if depth == 0 or not stack:
                roots.append(c)
                stack = [c]
            else:
                parent = stack[min(depth, len(stack)) - 1] if stack else None
                if parent is None:
                    roots.append(c)
                else:
                    parent.replies.append(c)
                if len(stack) > depth:
                    stack = stack[:depth]
                stack.append(c)
    if limit:
        return roots[:limit]
    return roots


def _redlib_one_comment(block: str, depth: int) -> Comment | None:
    auth_m = re.search(r'class="comment_author[^"]*"[^>]*href="/u(?:ser)?/([^"/]+)"', block)
    score_m = re.search(r'class="comment_score"[^>]*title="([^"]*)"', block)
    body_m = re.search(r'class="comment_body[^"]*">(.*?)</div>\s*</div>', block, re.S)
    if not body_m:
        body_m = re.search(r'class="comment_body[^"]*">(.*?)(?:<blockquote|</details>)', block, re.S)
    author = auth_m.group(1) if auth_m else "[deleted]"
    score = _parse_count(score_m.group(1)) if score_m else 0
    body = _strip_html(body_m.group(1)) if body_m else ""
    if not body and author == "[deleted]":
        return None
    return Comment(
        author=author,
        score=score,
        created_utc=_redlib_created(block),
        body=body,
        depth=depth,
    )


def _redlib_comments(subreddit: str, post_id: str, sort: str, limit: int) -> Thread:
    sub = subreddit or "r"
    path = f"/r/{sub}/comments/{post_id}/?sort={sort}"
    html_text = _redlib_fetch(path, not_found_label=f"no such post: {post_id}")
    # Post header lives in <div class="post highlighted"> ... <h1 class="post_title">
    post = _redlib_thread_post(html_text, post_id)
    comments = _redlib_parse_comments(html_text, limit)
    cm = re.search(r'id="comment_count">\s*([0-9.,kmKM]+)', html_text)
    total = _parse_count(cm.group(1)) if cm else len(comments)
    return Thread(post=post, comments=comments, total_comment_count=total)


def _redlib_thread_post(html_text: str, post_id: str) -> Post:
    i = html_text.find('class="post highlighted"')
    if i < 0:
        i = html_text.find('class="post"')
    block = html_text[i:i + 6000] if i >= 0 else html_text[:6000]
    tm = re.search(r'<h1 class="post_title">\s*(.*?)\s*</h1>', block, re.S)
    title_html = tm.group(1) if tm else ""
    # Drop any leading flair <a class="post_flair">…</a> — it isn't the title.
    title_html = re.sub(r'<a\s[^>]*class="post_flair"[^>]*>.*?</a>', "",
                        title_html, flags=re.S)
    title = _strip_html(title_html)
    sub_m = re.search(r'class="post_subreddit"[^>]*href="/r/([^"/]+)"', block)
    auth_m = re.search(r'class="post_author[^"]*"[^>]*href="/u(?:ser)?/([^"/]+)"', block)
    score_m = re.search(r'class="post_score"[^>]*title="([^"]*)"', block)
    body_m = re.search(r'class="post_body">(.*?)</div>\s*(?:<div class="post_media|<!-- POST|<footer|$)',
                       block, re.S)
    sub = sub_m.group(1) if sub_m else ""
    perm = f"https://reddit.com/r/{sub}/comments/{post_id}/" if sub else ""
    return Post(
        id=post_id,
        title=title,
        subreddit=sub,
        author=auth_m.group(1) if auth_m else "",
        score=_parse_count(score_m.group(1)) if score_m else 0,
        num_comments=0,
        created_utc=_redlib_created(block),
        url=perm,
        permalink=perm,
        selftext=_strip_html(body_m.group(1)) if body_m else "",
        is_self=True,
    )


def _redlib_user(name: str, limit: int) -> list[UserItem]:
    html_text = _redlib_fetch(f"/user/{name}", not_found_label=f"no such user: u/{name}")
    items: list[UserItem] = []
    # User page mixes posts and comments. Parse posts first.
    for p in _redlib_posts(html_text, "")[:limit]:
        items.append(UserItem(
            kind="post", title=p.title, subreddit=p.subreddit, score=p.score,
            created_utc=p.created_utc, permalink=p.permalink, body=p.selftext[:500],
        ))
    if len(items) < limit:
        for c in _redlib_parse_comments(html_text, limit):
            items.append(UserItem(
                kind="comment", title=f"comment in r/{c.author and ''}".strip() or "comment",
                subreddit="", score=c.score, created_utc=c.created_utc,
                permalink="", body=c.body,
            ))
    return items[:limit]


# ---------------------------------------------------------------------------
# URL / id parsing
# ---------------------------------------------------------------------------


def parse_post_ref(ref: str) -> tuple[str | None, str]:
    """Accept a full reddit/redlib URL, a /r/<sub>/comments/<id>/... path, a
    t3_<id>, or a bare <id>. Return (subreddit_or_None, post_id)."""
    ref = ref.strip()
    m = re.search(r"/r/([^/]+)/comments/([a-z0-9]+)", ref, re.I)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"/comments/([a-z0-9]+)", ref, re.I)
    if m:
        return None, m.group(1)
    if ref.startswith("t3_"):
        return None, ref[3:]
    if re.fullmatch(r"[a-z0-9]+", ref, re.I):
        return None, ref
    raise RedditError(f"could not parse a post id from {ref!r}")


# ---------------------------------------------------------------------------
# Dispatch wrappers (OAuth preferred, Redlib fallback)
# ---------------------------------------------------------------------------


def backend_name() -> str:
    return "oauth" if _have_oauth_creds() else "redlib"


def do_search(query, sort, time_filter, limit, subreddit):
    if _have_oauth_creds():
        return _oauth_search(query, sort, time_filter, limit, subreddit)
    return _redlib_search(query, sort, time_filter, limit, subreddit)


def do_subreddit(name, sort, time_filter, limit):
    if _have_oauth_creds():
        return _oauth_subreddit(name, sort, time_filter, limit)
    return _redlib_subreddit(name, sort, time_filter, limit)


def do_comments(ref, sort, limit):
    sub, pid = parse_post_ref(ref)
    if _have_oauth_creds():
        if sub is None:
            # oauth.reddit.com needs the subreddit for the comments path; the
            # /comments/<id> endpoint without a sub still resolves via /api/info.
            info = _oauth_get(f"/api/info", {"id": f"t3_{pid}", "raw_json": 1})
            ch = (info.get("data") or {}).get("children") or []
            if not ch:
                raise RedditNotFound(f"no such post: {pid}")
            sub = ch[0]["data"].get("subreddit")
        return _oauth_comments(sub, pid, sort, limit)
    return _redlib_comments(sub or "", pid, sort, limit)


def do_user(name, limit):
    if _have_oauth_creds():
        return _oauth_user(name, limit)
    return _redlib_user(name, limit)


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _fmt_dt(iso: str) -> str:
    if not iso:
        return ""
    try:
        d = dt.datetime.fromisoformat(iso)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return iso


def _wrap(s: str, width: int = 96, indent: str = "") -> str:
    import textwrap
    out = []
    for para in s.splitlines():
        if not para.strip():
            out.append("")
            continue
        out.extend(textwrap.wrap(para, width=width, initial_indent=indent,
                                 subsequent_indent=indent) or [indent + para])
    return "\n".join(out)


def render_posts(posts: list[Post]) -> str:
    if not posts:
        return "(no results)"
    lines = []
    for i, p in enumerate(posts, 1):
        lines.append(f"{i:>3}. {p.title}")
        meta = f"     r/{p.subreddit} · u/{p.author} · ▲{p.score} · 💬{p.num_comments}"
        if p.created_utc:
            meta += f" · {_fmt_dt(p.created_utc)}"
        lines.append(meta)
        if p.selftext:
            snip = p.selftext.replace("\n", " ")[:200]
            lines.append(_wrap(snip, width=92, indent="     "))
        lines.append(f"     {p.permalink or p.url}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_comment(c: Comment) -> str:
    pad = "  " * c.depth
    bullet = "└─" if c.depth else "•"
    head = f"{pad}{bullet} u/{c.author} · ▲{c.score}"
    if c.created_utc:
        head += f" · {_fmt_dt(c.created_utc)}"
    out = [head, _wrap(c.body, width=94 - len(pad), indent=pad + "   ")]
    for r in c.replies:
        out.append(render_comment(r))
    return "\n".join(out)


def render_thread(t: Thread) -> str:
    p = t.post
    out = [f"# {p.title}",
           f"r/{p.subreddit} · u/{p.author} · ▲{p.score} · {_fmt_dt(p.created_utc)}",
           p.permalink or p.url, ""]
    if p.selftext:
        out.append(_wrap(p.selftext, width=96))
        out.append("")
    out.append(f"── Comments ({t.total_comment_count}) ──")
    out.append("")
    for c in t.comments:
        out.append(render_comment(c))
        out.append("")
    return "\n".join(out).rstrip()


def render_user(items: list[UserItem]) -> str:
    if not items:
        return "(no activity)"
    lines = []
    for it in items:
        tag = "📝" if it.kind == "post" else "💬"
        lines.append(f"{tag} [{it.kind}] {it.title}  (r/{it.subreddit} · ▲{it.score} · {_fmt_dt(it.created_utc)})")
        if it.body:
            lines.append(_wrap(it.body.replace("\n", " ")[:200], width=92, indent="     "))
        if it.permalink:
            lines.append(f"     {it.permalink}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _json_dump(obj) -> None:
    if isinstance(obj, list):
        print(json.dumps([asdict(x) for x in obj], indent=2, ensure_ascii=False))
    elif dataclasses.is_dataclass(obj):
        print(json.dumps(asdict(obj), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_search(args) -> int:
    posts = do_search(args.query, args.sort, args.time, args.limit, args.subreddit)
    _log(f"backend={backend_name()} results={len(posts)}")
    if args.json:
        _json_dump(posts)
    else:
        if not posts:
            print("(no results)", file=sys.stderr)
            return 2
        print(render_posts(posts))
    return 0


def cmd_subreddit(args) -> int:
    posts = do_subreddit(args.name, args.sort, args.time, args.limit)
    _log(f"backend={backend_name()} results={len(posts)}")
    if args.json:
        _json_dump(posts)
    else:
        print(render_posts(posts))
    return 0


def cmd_comments(args) -> int:
    thread = do_comments(args.ref, args.sort, args.limit)
    _log(f"backend={backend_name()} comments={len(thread.comments)}")
    if args.json:
        _json_dump(thread)
    else:
        print(render_thread(thread))
    return 0


def cmd_user(args) -> int:
    items = do_user(args.name, args.limit)
    _log(f"backend={backend_name()} items={len(items)}")
    if args.json:
        _json_dump(items)
    else:
        print(render_user(items))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="emit JSON")
    common.add_argument("--limit", type=int, default=10, help="max items (default 10)")
    common.add_argument("-v", "--verbose", action="store_true",
                        help="log backend + fetches to stderr")

    p = argparse.ArgumentParser(
        prog="reddit",
        description="Reddit search/browse CLI — OAuth when creds present, "
                    "else Redlib HTML fallback (flaky). Read-only.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", parents=[common], help="search Reddit")
    s.add_argument("query")
    s.add_argument("--subreddit", "-r", help="restrict to a subreddit")
    s.add_argument("--sort", default="relevance",
                   choices=["relevance", "hot", "new", "top", "comments"])
    s.add_argument("--time", default="all",
                   choices=["hour", "day", "week", "month", "year", "all"])
    s.set_defaults(func=cmd_search)

    sr = sub.add_parser("subreddit", parents=[common], help="browse a subreddit")
    sr.add_argument("name")
    sr.add_argument("--sort", default="hot",
                    choices=["hot", "new", "top", "rising", "controversial"])
    sr.add_argument("--time", default="day",
                    choices=["hour", "day", "week", "month", "year", "all"])
    sr.set_defaults(func=cmd_subreddit)

    c = sub.add_parser("comments", parents=[common], help="a post + its comments")
    c.add_argument("ref", help="post URL, /r/.../comments/<id>/..., t3_<id>, or bare id")
    c.add_argument("--sort", default="confidence",
                   choices=["confidence", "top", "new", "controversial", "old", "qa", "best"])
    c.set_defaults(func=cmd_comments)

    u = sub.add_parser("user", parents=[common], help="a user's recent activity")
    u.add_argument("name")
    u.set_defaults(func=cmd_user)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    global _verbose
    _verbose = bool(getattr(args, "verbose", False))
    try:
        return args.func(args) or 0
    except RedditNotFound as e:
        print(f"not found: {e}", file=sys.stderr)
        return 2
    except RedditError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
