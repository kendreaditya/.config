#!/usr/bin/env python3
"""
interviewcoder.py — read-only CLI for interviewcoder.co

Pulls posts and questions by parsing the Next.js Flight payload that's
embedded in each page (the `self.__next_f.push([...])` script blocks).
No login, no cookies, no API key. Same approach as the `blind` skill.

Commands:
  list                     First page of questions (filterable)
  read <id>                One post + its structured questions
  companies                Company directory with question counts
  search <query>           Client-side search across the first N pages
  export <id> [--format]   Dump post + questions to md or json

Common flags: --json, --limit N, -v
"""

from __future__ import annotations

import argparse
import dataclasses
import gzip
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)
BASE = "https://www.interviewcoder.co"


class ICError(Exception):
    pass


class ICNotFound(ICError):
    pass


def fetch(path: str, *, debug: bool = False) -> str:
    if path.startswith("http"):
        url = path
    else:
        url = BASE + path
    headers = {
        "user-agent": UA,
        "accept": "text/html,application/xhtml+xml",
        "accept-encoding": "gzip",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ICNotFound(f"not found: {url}") from e
        raise ICError(f"HTTP {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise ICError(f"network error for {url}: {e.reason}") from e
    raw = resp.read()
    if resp.headers.get("content-encoding") == "gzip":
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8", errors="replace")
    if debug:
        sys.stderr.write(f"[fetch] {url} -> {len(text)} bytes\n")
    return text


# ---------------------------------------------------------------------------
# Flight payload parser
#
# Next.js streams RSC data to the browser via repeated
#     self.__next_f.push([1, "<flight chunk text>"])
# script tags. Each chunk text is a series of newline-separated rows:
#     <hex_id>:<value>
# where <value> is either a JSON value (for components/objects) or
#     T<hex_length>,<literal text>
# (a literal text payload).
#
# String fields can reference other chunks by their id, e.g. "content":"$21"
# means "look up chunk 21". We resolve those refs after parsing.
# ---------------------------------------------------------------------------

NEXT_F_RE = re.compile(
    r'self\.__next_f\.push\((\[\d+,"(?:[^"\\]|\\.)*"\])\)',
    re.DOTALL,
)
HEX_REF_RE = re.compile(r"^[0-9a-f]+$")
ROW_HEAD_RE_B = re.compile(rb"([0-9a-f]+):")
_DECODER = json.JSONDecoder()


def parse_flight(html_text: str) -> dict[str, Any]:
    """Parse the React Server Components Flight stream out of the HTML.

    The stream is a concatenation of `<hex_id>:<value>` rows. Values are
    either:
      * `T<hex_byte_length>,<literal-text>` — length-prefixed in UTF-8 bytes
      * an `I[...]` import row — opaque to us
      * a JSON value (object/array/string/number/null) ending at `\n` or EOF

    Length is in UTF-8 bytes, so we work on the byte sequence rather than
    Python `str` (which counts code points). We also can't split on `\n`
    naively: JSON values can contain text like "13:24" that looks like a
    row header.
    """
    blob = bytearray()
    for m in NEXT_F_RE.finditer(html_text):
        try:
            arr = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(arr, list) and len(arr) >= 2 and isinstance(arr[1], str):
            blob.extend(arr[1].encode("utf-8"))
    blob_b = bytes(blob)

    chunks: dict[str, Any] = {}
    i = 0
    n = len(blob_b)
    while i < n:
        while i < n and blob_b[i : i + 1] == b"\n":
            i += 1
        if i >= n:
            break
        head = ROW_HEAD_RE_B.match(blob_b, i)
        if not head:
            nl = blob_b.find(b"\n", i)
            if nl < 0:
                break
            i = nl + 1
            continue
        cid = head.group(1).decode("ascii")
        i = head.end()
        if i >= n:
            break
        ch = blob_b[i : i + 1]
        if ch == b"T":
            comma = blob_b.find(b",", i)
            if comma < 0:
                break
            try:
                length = int(blob_b[i + 1 : comma].decode("ascii"), 16)
            except ValueError:
                length = 0
            start = comma + 1
            end = start + length
            chunks[cid] = blob_b[start:end].decode("utf-8", errors="replace")
            i = end
        elif ch == b"I":
            nl = blob_b.find(b"\n", i)
            if nl < 0:
                nl = n
            chunks[cid] = blob_b[i:nl].decode("utf-8", errors="replace")
            i = nl
        else:
            tail = blob_b[i:].decode("utf-8", errors="replace")
            try:
                value, end_char = _DECODER.raw_decode(tail)
                consumed = len(tail[:end_char].encode("utf-8"))
                chunks[cid] = value
                i += consumed
            except json.JSONDecodeError:
                nl = blob_b.find(b"\n", i)
                if nl < 0:
                    nl = n
                chunks[cid] = blob_b[i:nl].decode("utf-8", errors="replace")
                i = nl
    return chunks


def resolve_refs(value: Any, chunks: dict[str, Any], depth: int = 0) -> Any:
    if depth > 8:
        return value
    if isinstance(value, str):
        if value == "$undefined":
            return None
        if len(value) >= 2 and value[0] == "$" and HEX_REF_RE.match(value[1:]):
            ref = value[1:]
            if ref in chunks:
                return resolve_refs(chunks[ref], chunks, depth + 1)
        return value
    if isinstance(value, list):
        return [resolve_refs(v, chunks, depth + 1) for v in value]
    if isinstance(value, dict):
        return {k: resolve_refs(v, chunks, depth + 1) for k, v in value.items()}
    return value


def find_props(chunks: dict[str, Any], required_key: str) -> dict[str, Any] | None:
    """Walk all chunks; return the first dict-of-props containing required_key.

    Flight component rows look like ["$", "$Lxx", null, {props…}]. We scan
    every chunk that's a list of that shape and check the props dict.
    """
    for value in chunks.values():
        if isinstance(value, list) and len(value) >= 4 and isinstance(value[3], dict):
            if required_key in value[3]:
                return value[3]
    return None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Question:
    id: str
    question_number: int | None
    title: str
    description: str
    difficulty: str | None
    leetcode_ref: str | None
    tags: list[str]
    created_at: str | None


@dataclass
class Post:
    id: str
    title: str
    author: str | None
    company: str | None
    position: str | None
    period: str | None
    job_type: str | None
    user_type: str | None
    interview_stage: str | None
    outcome: str | None
    content: str
    posted_at_original: str | None
    created_at: str | None
    url: str | None
    source_url: str | None
    category: str | None
    views_count: int
    likes_count: int
    bookmarks_count: int
    comments_count: int
    questions: list[Question] = field(default_factory=list)


@dataclass
class Article:
    post: Post
    markdown: str | None
    has_access: bool
    is_authenticated: bool


# ---------------------------------------------------------------------------
# Mappers
# ---------------------------------------------------------------------------


def _q(raw: dict[str, Any]) -> Question:
    return Question(
        id=raw.get("id", ""),
        question_number=raw.get("question_number"),
        title=(raw.get("title") or "").strip(),
        description=(raw.get("description") or "").strip(),
        difficulty=raw.get("difficulty"),
        leetcode_ref=raw.get("leetcode_ref"),
        tags=list(raw.get("tags") or []),
        created_at=raw.get("created_at"),
    )


def _post(raw: dict[str, Any]) -> Post:
    pid = raw.get("id", "")
    return Post(
        id=pid,
        title=(raw.get("title") or "").strip(),
        author=raw.get("author"),
        company=raw.get("company"),
        position=raw.get("position"),
        period=raw.get("period"),
        job_type=raw.get("job_type"),
        user_type=raw.get("user_type"),
        interview_stage=raw.get("interview_stage"),
        outcome=raw.get("outcome"),
        content=(raw.get("content") or "").strip(),
        posted_at_original=raw.get("posted_at_original"),
        created_at=raw.get("created_at"),
        url=f"{BASE}/questions/{pid}" if pid else None,
        source_url=raw.get("url"),
        category=raw.get("category"),
        views_count=int(raw.get("views_count") or 0),
        likes_count=int(raw.get("likes_count") or 0),
        bookmarks_count=int(raw.get("bookmarks_count") or 0),
        comments_count=int(raw.get("comments_count") or 0),
        questions=[_q(q) for q in (raw.get("questions") or [])],
    )


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------


def _build_list_path(
    *,
    page: int = 1,
    company: str | None = None,
    job_type: str | None = None,
    stage: str | None = None,
    outcome: str | None = None,
    sort: str | None = None,
) -> str:
    params: list[tuple[str, str]] = [("page", str(page))]
    if company:
        params.append(("companyName", company))
    if job_type:
        params.append(("jobType", job_type))
    if stage:
        params.append(("stage", stage))
    if outcome:
        params.append(("outcome", outcome))
    if sort:
        params.append(("sort", sort))
    return "/questions?" + urllib.parse.urlencode(params)


def fetch_listing(
    *,
    page: int = 1,
    company: str | None = None,
    job_type: str | None = None,
    stage: str | None = None,
    outcome: str | None = None,
    sort: str | None = None,
    debug: bool = False,
) -> dict[str, Any]:
    path = _build_list_path(
        page=page,
        company=company,
        job_type=job_type,
        stage=stage,
        outcome=outcome,
        sort=sort,
    )
    html = fetch(path, debug=debug)
    chunks = parse_flight(html)
    props = find_props(chunks, "posts")
    if props is None:
        raise ICError("could not locate posts in page payload")
    props = resolve_refs(props, chunks)
    raw_posts = props.get("posts") or []
    posts = [_post(p) for p in raw_posts if isinstance(p, dict)]
    companies = props.get("companiesWithCounts") or []
    return {
        "posts": posts,
        "companies": companies,
        "total_pages": props.get("totalPages") or 1,
        "current_page": props.get("currentPage") or page,
        "filters": props.get("filters") or {},
    }


def fetch_post(post_id: str, *, debug: bool = False) -> Article:
    pid = _normalize_id(post_id)
    html = fetch(f"/questions/{pid}", debug=debug)
    chunks = parse_flight(html)
    props = find_props(chunks, "post")
    if props is None:
        raise ICNotFound(f"post not found: {pid}")
    props = resolve_refs(props, chunks)
    raw = props.get("post")
    if not isinstance(raw, dict):
        raise ICNotFound(f"post not found: {pid}")
    post = _post(raw)
    markdown = raw.get("markdown")
    if isinstance(markdown, str):
        markdown = markdown.strip()
    return Article(
        post=post,
        markdown=markdown if isinstance(markdown, str) else None,
        has_access=bool(props.get("hasAccess", False)),
        is_authenticated=bool(props.get("isAuthenticated", False)),
    )


UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _normalize_id(s: str) -> str:
    if s.startswith("http"):
        m = UUID_RE.search(s)
        if not m:
            raise ICError(f"no UUID found in URL: {s}")
        return m.group(0).lower()
    if UUID_RE.fullmatch(s):
        return s.lower()
    raise ICError(f"not a valid post id or URL: {s}")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _trim(s: str, n: int) -> str:
    s = s.replace("\r\n", "\n")
    if len(s) <= n:
        return s
    return s[:n].rstrip() + f" […+{len(s) - n} chars]"


def render_post_summary(p: Post, *, content_chars: int = 280) -> str:
    tags = []
    if p.company:
        tags.append(p.company)
    if p.position:
        tags.append(p.position)
    if p.job_type:
        tags.append(p.job_type)
    if p.interview_stage:
        tags.append(p.interview_stage)
    header = " · ".join(filter(None, tags))
    meta = []
    if p.period:
        meta.append(p.period)
    if p.posted_at_original:
        meta.append(p.posted_at_original)
    if p.author:
        meta.append(f"@{p.author}")
    meta_line = " · ".join(meta)
    engagement = (
        f"♥ {p.likes_count}  🔖 {p.bookmarks_count}  💬 {p.comments_count}  👁 {p.views_count}"
    )
    body = _trim(p.content, content_chars) if p.content else ""
    qs = f"\n  Questions ({len(p.questions)}):" if p.questions else ""
    for q in p.questions[:6]:
        diff = f" [{q.difficulty}]" if q.difficulty else ""
        qs += f"\n    {q.question_number or '?'}.{diff} {_trim(q.title, 100)}"
    if len(p.questions) > 6:
        qs += f"\n    … +{len(p.questions) - 6} more"
    return (
        f"\n{p.title}\n"
        f"  {header}\n"
        + (f"  {meta_line}\n" if meta_line else "")
        + f"  {engagement}\n"
        + (f"  {body}\n" if body else "")
        + qs
        + f"\n  {p.url}"
    )


def render_listing(result: dict[str, Any], *, limit: int | None = None) -> str:
    posts = result["posts"]
    if limit:
        posts = posts[:limit]
    page = result["current_page"]
    total = result["total_pages"]
    filters = result.get("filters") or {}
    active = {
        k: v
        for k, v in filters.items()
        if isinstance(v, str) and v and v != "$undefined"
    }
    fline = (
        " · ".join(f"{k}={v}" for k, v in active.items()) if active else "(no filters)"
    )
    out = [f"page {page}/{total}  {fline}  [{len(posts)} posts]"]
    for p in posts:
        out.append(render_post_summary(p))
    return "\n".join(out)


def render_article(a: Article) -> str:
    p = a.post
    body = (a.markdown or p.content or "").strip()
    qs_lines = []
    for q in p.questions:
        head = f"{q.question_number or '?'}."
        if q.difficulty:
            head += f" [{q.difficulty}]"
        head += f" {q.title}"
        qs_lines.append(head)
        if q.description and q.description != q.title:
            qs_lines.append("    " + q.description.replace("\n", "\n    "))
        if q.tags:
            qs_lines.append("    tags: " + ", ".join(q.tags))
        if q.leetcode_ref:
            qs_lines.append("    leetcode: " + q.leetcode_ref)
    tags = []
    for label, value in (
        ("Company", p.company),
        ("Position", p.position),
        ("Stage", p.interview_stage),
        ("Period", p.period),
        ("Type", p.job_type),
        ("Level", p.user_type),
        ("Outcome", p.outcome),
    ):
        if value:
            tags.append(f"{label}: {value}")
    meta_line = " · ".join(tags)
    posted = p.posted_at_original or p.created_at or ""
    author = f"@{p.author}" if p.author else ""
    parts = [
        f"# {p.title}",
        f"{meta_line}",
        f"{author}  {posted}".strip(),
        f"♥ {p.likes_count}  🔖 {p.bookmarks_count}  💬 {p.comments_count}  👁 {p.views_count}",
        "",
        body,
        "",
    ]
    if qs_lines:
        parts.append("## Questions")
        parts.extend(qs_lines)
        parts.append("")
    parts.append(f"URL:        {p.url}")
    if p.source_url:
        parts.append(f"Source:     {p.source_url}")
    if not a.has_access:
        parts.append("")
        parts.append(
            "Note: hasAccess=false. interviewcoder.co paywalls some features "
            "for logged-out users; the post body is still returned in full."
        )
    return "\n".join(parts)


def render_companies(entries: Iterable[dict[str, Any]], *, limit: int | None = None) -> str:
    rows = [e for e in entries if isinstance(e, dict)]
    if limit:
        rows = rows[:limit]
    if not rows:
        return "(no companies)"
    width = max((len(str(e.get("name", ""))) for e in rows), default=8)
    out = []
    for e in rows:
        name = str(e.get("name", ""))
        count = e.get("count", 0)
        out.append(f"  {name:<{width}}  {count}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_markdown(a: Article) -> str:
    return render_article(a)


def export_json(a: Article) -> str:
    return json.dumps(
        {
            "post": dataclasses.asdict(a.post),
            "markdown": a.markdown,
            "has_access": a.has_access,
            "is_authenticated": a.is_authenticated,
        },
        indent=2,
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="emit structured JSON")
    p.add_argument("--limit", type=int, default=None, help="cap output to N items")
    p.add_argument("-v", "--verbose", action="store_true", help="log fetched URLs to stderr")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="interviewcoder",
        description="Read-only CLI for interviewcoder.co",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list questions (one page)")
    p_list.add_argument("--company", help="filter by companyName (e.g. Apple)")
    p_list.add_argument("--job-type", dest="job_type", help="Fulltime, Intern, …")
    p_list.add_argument("--stage", help="Phone Screen, Onsite, OA, …")
    p_list.add_argument("--outcome", help="filter by outcome")
    p_list.add_argument("--sort", help="oldest, most-bookmarked, … (default newest)")
    p_list.add_argument("--page", type=int, default=1)
    _add_common(p_list)

    p_read = sub.add_parser("read", help="fetch one post + its questions")
    p_read.add_argument("id", help="post UUID or full /questions/<uuid> URL")
    _add_common(p_read)

    p_companies = sub.add_parser("companies", help="list company directory + counts")
    _add_common(p_companies)

    p_search = sub.add_parser("search", help="client-side search across recent pages")
    p_search.add_argument("query")
    p_search.add_argument("--company", help="restrict to a company before searching")
    p_search.add_argument("--pages", type=int, default=3, help="pages to scan (default 3)")
    _add_common(p_search)

    p_export = sub.add_parser("export", help="dump one post to md or json")
    p_export.add_argument("id")
    p_export.add_argument("--format", choices=("md", "json"), default="md")
    p_export.add_argument("-v", "--verbose", action="store_true")

    args = ap.parse_args(argv)
    debug = getattr(args, "verbose", False)

    try:
        if args.cmd == "list":
            res = fetch_listing(
                page=args.page,
                company=args.company,
                job_type=args.job_type,
                stage=args.stage,
                outcome=args.outcome,
                sort=args.sort,
                debug=debug,
            )
            if args.json:
                payload = {
                    "current_page": res["current_page"],
                    "total_pages": res["total_pages"],
                    "filters": res["filters"],
                    "posts": [dataclasses.asdict(p) for p in res["posts"][: args.limit or None]],
                }
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(render_listing(res, limit=args.limit))
            return 0

        if args.cmd == "read":
            art = fetch_post(args.id, debug=debug)
            if args.json:
                print(export_json(art))
            else:
                print(render_article(art))
            return 0

        if args.cmd == "companies":
            res = fetch_listing(page=1, debug=debug)
            companies = res.get("companies") or []
            if args.json:
                print(json.dumps(companies[: args.limit or None], indent=2, ensure_ascii=False))
            else:
                print(render_companies(companies, limit=args.limit))
            return 0

        if args.cmd == "search":
            q = args.query.lower()
            hits: list[Post] = []
            for page in range(1, max(1, args.pages) + 1):
                res = fetch_listing(page=page, company=args.company, debug=debug)
                for p in res["posts"]:
                    hay = " ".join(
                        s for s in (
                            p.title,
                            p.content,
                            p.company,
                            p.position,
                            p.interview_stage,
                            " ".join(q2.title for q2 in p.questions),
                            " ".join(t for q2 in p.questions for t in q2.tags),
                        ) if s
                    ).lower()
                    if q in hay:
                        hits.append(p)
                if page >= (res.get("total_pages") or 1):
                    break
                if args.limit and len(hits) >= args.limit:
                    break
            if args.limit:
                hits = hits[: args.limit]
            if args.json:
                print(json.dumps([dataclasses.asdict(p) for p in hits], indent=2, ensure_ascii=False))
            else:
                print(f"{len(hits)} hit(s) for {args.query!r} across {args.pages} page(s)")
                for p in hits:
                    print(render_post_summary(p))
            return 0

        if args.cmd == "export":
            art = fetch_post(args.id, debug=debug)
            if args.format == "json":
                print(export_json(art))
            else:
                print(export_markdown(art))
            return 0

    except ICNotFound as e:
        sys.stderr.write(f"not found: {e}\n")
        return 2
    except ICError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    except KeyboardInterrupt:
        return 130

    return 1


if __name__ == "__main__":
    sys.exit(main())
