#!/usr/bin/env python3
"""
lcsearch — minimal LeetCode search & read CLI (read-only, no auth)

Hits the public surface of leetcode.com:
  - REST /api/problems/all/                (the full problem catalog)
  - POST /graphql/ for a handful of public operations

Reverse-engineered from a logged-in HAR, then filtered down to the
ops that return data for an anonymous client. Filtered problem search
(problemsetQuestionListV2) and company question lists
(favoriteQuestionList for COMPANY_FAVORITE slugs) require a session
cookie and are NOT exposed here — only the public substring search
over the REST catalog and company-list metadata.

Commands:
  daily                          Today's daily coding challenge
  problem <slug-or-id>           Full problem (statement, snippets, tags)
  search <query>                 Substring search over the problem catalog
  list                           Filter the problem catalog (no keyword)
  discuss <query>                Search discussion posts
  feed [tag-slug]                Discussion feed (optionally tag-filtered)
  read <topic-id-or-url>         Full discuss post + comment thread
  comments <topic-id-or-url>     Just the comment thread
  company <slug>                 Company list metadata
  tags                           Hot discussion tags
  export <topic-id-or-url>       Dump discuss post + comments to md/json
  export-problem <slug-or-id>    Dump a problem to md/json

Common flags: --json, --limit N, -v
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
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

BASE = "https://leetcode.com"
GQL = f"{BASE}/graphql/"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)

_verbose = False


class LCError(Exception):
    pass


class LCNotFound(LCError):
    pass


def _log(msg: str) -> None:
    if _verbose:
        print(f"[leetcode] {msg}", file=sys.stderr)


def _http(url: str, *, data: bytes | None = None, headers: dict | None = None) -> bytes:
    hdrs = {"user-agent": UA, "accept": "*/*", "referer": f"{BASE}/"}
    if headers:
        hdrs.update(headers)
    _log(f"{'POST' if data else 'GET'} {url}")
    req = urllib.request.Request(url, data=data, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        body = e.read()[:400].decode("utf-8", "replace")
        raise LCError(f"HTTP {e.code} {e.reason} for {url}: {body}") from e
    except urllib.error.URLError as e:
        raise LCError(f"network error for {url}: {e}") from e


def gql(query: str, variables: dict, operation: str) -> dict:
    body = json.dumps(
        {"query": query, "variables": variables, "operationName": operation}
    ).encode()
    raw = _http(
        GQL,
        data=body,
        headers={"content-type": "application/json", "x-operation-name": operation},
    )
    try:
        payload = json.loads(raw)
    except Exception as e:
        raise LCError(f"non-JSON response for {operation}: {raw[:200]!r}") from e
    if payload.get("errors"):
        msg = payload["errors"][0].get("message", "")
        if "Sign in" in msg or "Register" in msg or "permission" in msg.lower():
            raise LCError(
                f"{operation} requires authentication "
                f"(LeetCode error: {msg!r}). This skill is anonymous-only."
            )
        raise LCError(f"GraphQL error on {operation}: {msg}")
    return payload.get("data") or {}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Problem:
    id: int
    frontend_id: str
    title: str
    title_slug: str
    difficulty: str
    paid_only: bool
    ac_rate: float | None
    total_accepted: int | None
    total_submitted: int | None
    url: str
    tags: list[str] = field(default_factory=list)


@dataclass
class CodeSnippet:
    lang: str
    lang_slug: str
    code: str


@dataclass
class ProblemDetail:
    problem: Problem
    content_html: str
    content_text: str
    hints: list[str]
    likes: int | None
    dislikes: int | None
    similar_questions: list[dict]
    example_testcases: str
    code_snippets: list[CodeSnippet]


@dataclass
class DiscussPost:
    topic_id: int
    uuid: str
    title: str
    slug: str
    summary: str
    author: str
    author_slug: str
    created_at: str
    hit_count: int
    upvotes: int
    comment_count: int
    tags: list[dict]
    url: str


@dataclass
class Comment:
    id: int
    author: str
    content: str
    created_at: str
    vote_count: int
    num_children: int
    pinned: bool


@dataclass
class Article:
    post: DiscussPost
    content: str
    comments: list[Comment]
    total_comment_count: int


@dataclass
class CompanyInfo:
    slug: str
    name: str
    description: str
    question_count: int
    collect_count: int
    is_public: bool
    favorite_type: str
    last_modified: str
    creator: str
    generated_slugs: list[dict]
    position_role_tags: list[dict]
    url: str


# ---------------------------------------------------------------------------
# REST: problem catalog
# ---------------------------------------------------------------------------

_DIFF_MAP_REST = {1: "Easy", 2: "Medium", 3: "Hard"}
_PROBLEM_CACHE_PATH = os.path.expanduser("~/.cache/leetcode/problems.json")
_PROBLEM_CACHE_TTL = 24 * 3600


def fetch_problem_catalog(force: bool = False) -> list[dict]:
    """Return every entry from /api/problems/all/, cached to disk for a day."""
    if not force and os.path.exists(_PROBLEM_CACHE_PATH):
        age = time.time() - os.path.getmtime(_PROBLEM_CACHE_PATH)
        if age < _PROBLEM_CACHE_TTL:
            _log(f"using cached catalog ({age:.0f}s old)")
            with open(_PROBLEM_CACHE_PATH) as f:
                return json.load(f)
    raw = _http(f"{BASE}/api/problems/all/")
    payload = json.loads(raw)
    pairs = payload.get("stat_status_pairs", [])
    os.makedirs(os.path.dirname(_PROBLEM_CACHE_PATH), exist_ok=True)
    with open(_PROBLEM_CACHE_PATH, "w") as f:
        json.dump(pairs, f)
    return pairs


def _pair_to_problem(pair: dict) -> Problem:
    stat = pair["stat"]
    diff = _DIFF_MAP_REST.get(pair.get("difficulty", {}).get("level"), "Unknown")
    ac = stat.get("total_acs")
    sub = stat.get("total_submitted")
    ac_rate = (ac / sub) if (ac and sub) else None
    slug = stat["question__title_slug"]
    return Problem(
        id=stat["question_id"],
        frontend_id=str(stat["frontend_question_id"]),
        title=stat["question__title"],
        title_slug=slug,
        difficulty=diff,
        paid_only=bool(pair.get("paid_only")),
        ac_rate=ac_rate,
        total_accepted=ac,
        total_submitted=sub,
        url=f"{BASE}/problems/{slug}/",
    )


def search_problems(
    query: str,
    *,
    difficulty: str | None = None,
    paid: bool | None = None,
    limit: int = 20,
) -> list[Problem]:
    pairs = fetch_problem_catalog()
    q = query.lower().strip()
    out: list[Problem] = []
    for pair in pairs:
        p = _pair_to_problem(pair)
        if q and q not in p.title.lower() and q not in p.title_slug:
            # also match by frontend id
            if q != p.frontend_id:
                continue
        if difficulty and p.difficulty.lower() != difficulty.lower():
            continue
        if paid is True and not p.paid_only:
            continue
        if paid is False and p.paid_only:
            continue
        out.append(p)
        if limit and len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# GraphQL: question detail
# ---------------------------------------------------------------------------

Q_QUESTION_DETAIL = """
query questionDetail($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    titleSlug
    difficulty
    isPaidOnly
    content
    likes
    dislikes
    stats
    hints
    topicTags { name slug }
    similarQuestions
    exampleTestcases
    codeSnippets { lang langSlug code }
  }
}
"""


def _slug_from_arg(arg: str) -> str:
    """Accept a title slug, problem number, or full URL."""
    arg = arg.strip()
    # URL
    m = re.search(r"/problems/([a-z0-9-]+)", arg)
    if m:
        return m.group(1)
    # Pure number — look up in catalog
    if arg.isdigit():
        for pair in fetch_problem_catalog():
            if str(pair["stat"]["frontend_question_id"]) == arg:
                return pair["stat"]["question__title_slug"]
        raise LCNotFound(f"no problem with frontend id #{arg}")
    return arg.lower().replace(" ", "-")


def fetch_problem_detail(slug: str) -> ProblemDetail:
    data = gql(Q_QUESTION_DETAIL, {"titleSlug": slug}, "questionDetail")
    q = data.get("question")
    if not q:
        raise LCNotFound(f"no problem with slug {slug!r}")
    stats = {}
    try:
        stats = json.loads(q.get("stats") or "{}")
    except Exception:
        pass
    similar = []
    try:
        similar = json.loads(q.get("similarQuestions") or "[]")
    except Exception:
        pass
    p = Problem(
        id=int(q["questionId"]),
        frontend_id=q["questionFrontendId"],
        title=q["title"],
        title_slug=q["titleSlug"],
        difficulty=q["difficulty"],
        paid_only=bool(q.get("isPaidOnly")),
        ac_rate=(
            stats.get("totalAcceptedRaw", 0) / stats.get("totalSubmissionRaw", 1)
            if stats.get("totalSubmissionRaw")
            else None
        ),
        total_accepted=stats.get("totalAcceptedRaw"),
        total_submitted=stats.get("totalSubmissionRaw"),
        url=f"{BASE}/problems/{q['titleSlug']}/",
        tags=[t["name"] for t in (q.get("topicTags") or [])],
    )
    return ProblemDetail(
        problem=p,
        content_html=q.get("content") or "",
        content_text=html_to_text(q.get("content") or ""),
        hints=q.get("hints") or [],
        likes=q.get("likes"),
        dislikes=q.get("dislikes"),
        similar_questions=similar,
        example_testcases=q.get("exampleTestcases") or "",
        code_snippets=[
            CodeSnippet(lang=s["lang"], lang_slug=s["langSlug"], code=s["code"])
            for s in (q.get("codeSnippets") or [])
        ],
    )


# ---------------------------------------------------------------------------
# GraphQL: daily challenge
# ---------------------------------------------------------------------------

Q_DAILY = """
query questionOfToday {
  activeDailyCodingChallengeQuestion {
    date
    link
    question {
      questionFrontendId
      titleSlug
      title
      difficulty
    }
  }
}
"""


def fetch_daily() -> tuple[str, Problem]:
    data = gql(Q_DAILY, {}, "questionOfToday")
    today = data.get("activeDailyCodingChallengeQuestion") or {}
    q = today.get("question") or {}
    p = Problem(
        id=0,
        frontend_id=q.get("questionFrontendId", "?"),
        title=q.get("title", "?"),
        title_slug=q.get("titleSlug", ""),
        difficulty=q.get("difficulty", "Unknown"),
        paid_only=False,
        ac_rate=None,
        total_accepted=None,
        total_submitted=None,
        url=f"{BASE}{today.get('link', '/problems/' + q.get('titleSlug', '') + '/')}",
    )
    return today.get("date", ""), p


# ---------------------------------------------------------------------------
# GraphQL: discuss
# ---------------------------------------------------------------------------

Q_DISCUSS_FEED = """
query discussPostItems($orderBy: ArticleOrderByEnum, $keywords: [String]!, $tagSlugs: [String!], $skip: Int, $first: Int) {
  ugcArticleDiscussionArticles(orderBy: $orderBy, keywords: $keywords, tagSlugs: $tagSlugs, skip: $skip, first: $first) {
    totalNum
    pageInfo { hasNextPage }
    edges {
      node {
        uuid title slug summary topicId hitCount createdAt
        author { userName userSlug realName }
        tags { name slug tagType }
        reactions { count reactionType }
        topic { topLevelCommentCount }
      }
    }
  }
}
"""

Q_DISCUSS_DETAIL = """
query discussPostDetail($topicId: ID!) {
  ugcArticleDiscussionArticle(topicId: $topicId) {
    uuid title slug summary content topicId hitCount createdAt
    author { userName userSlug realName }
    tags { name slug tagType }
    topic { id topLevelCommentCount }
    reactions { count reactionType }
  }
}
"""

Q_DISCUSS_COMMENTS = """
query questionDiscussComments($topicId: Int!, $orderBy: String = "best", $pageNo: Int = 1, $numPerPage: Int = 10) {
  topicComments(topicId: $topicId, orderBy: $orderBy, pageNo: $pageNo, numPerPage: $numPerPage) {
    data {
      id
      pinned
      post {
        id
        content
        creationDate
        voteCount
        author { username profile { realName } }
      }
      numChildren
    }
    totalNum
  }
}
"""

Q_DISCUSS_HOT_TAGS = """
query discussExploreItems {
  ugcArticleDiscussionHotTags {
    id name slug
    discussions { topicId slug title }
  }
}
"""

ORDER_MAP = {"hot": "HOT", "recent": "MOST_RECENT", "votes": "MOST_VOTES"}

# topicComments uses a different vocabulary than the discuss-article feed.
# Valid values seen in the wild: best, hot, newest_to_oldest, most_votes.
COMMENT_ORDER_MAP = {
    "hot": "hot",
    "best": "best",
    "recent": "newest_to_oldest",
    "newest": "newest_to_oldest",
    "votes": "most_votes",
}


def _post_node_to_dataclass(node: dict) -> DiscussPost:
    author = node.get("author") or {}
    upvotes = 0
    for r in node.get("reactions") or []:
        if r.get("reactionType") == "UPVOTE":
            upvotes = r.get("count", 0)
            break
    slug = node.get("slug", "")
    return DiscussPost(
        topic_id=int(node["topicId"]),
        uuid=node.get("uuid", ""),
        title=node.get("title", ""),
        slug=slug,
        summary=node.get("summary", "") or "",
        author=author.get("userName") or author.get("realName") or "",
        author_slug=author.get("userSlug", ""),
        created_at=node.get("createdAt", ""),
        hit_count=node.get("hitCount", 0) or 0,
        upvotes=upvotes,
        comment_count=(node.get("topic") or {}).get("topLevelCommentCount", 0) or 0,
        tags=[
            {"name": t["name"], "slug": t["slug"], "type": t.get("tagType")}
            for t in (node.get("tags") or [])
        ],
        url=f"{BASE}/discuss/post/{slug}/" if slug else f"{BASE}/discuss/topic/{node['topicId']}",
    )


def search_discuss(
    keyword: str,
    *,
    tag_slugs: list[str] | None = None,
    order: str = "hot",
    skip: int = 0,
    first: int = 25,
) -> tuple[int, bool, list[DiscussPost]]:
    order_v = ORDER_MAP.get(order, "HOT")
    data = gql(
        Q_DISCUSS_FEED,
        {
            "orderBy": order_v,
            "keywords": [keyword] if keyword else [""],
            "tagSlugs": tag_slugs or [],
            "skip": skip,
            "first": first,
        },
        "discussPostItems",
    )
    node = data.get("ugcArticleDiscussionArticles") or {}
    total = node.get("totalNum", 0) or 0
    has_more = (node.get("pageInfo") or {}).get("hasNextPage", False)
    edges = node.get("edges") or []
    return total, has_more, [_post_node_to_dataclass(e["node"]) for e in edges]


def _topic_id_from_arg(arg: str) -> int:
    arg = arg.strip()
    # /discuss/topic/12345 or /discuss/post/some-slug-xxxx — accept either
    m = re.search(r"/discuss/topic/(\d+)", arg)
    if m:
        return int(m.group(1))
    # Bare int
    if arg.isdigit():
        return int(arg)
    # Post slug → need to resolve via search. We'll do a discuss search by the
    # last token of the slug as a keyword fallback, but the cleanest path is
    # for the user to pass the numeric topic ID. Make it explicit.
    raise LCError(
        f"could not extract numeric topic id from {arg!r}. "
        "Pass either a numeric topicId, a /discuss/topic/<id> URL, or "
        "find the post via `leetcode discuss <query>` to get its topicId."
    )


def fetch_post_detail(topic_id: int) -> DiscussPost | None:
    data = gql(Q_DISCUSS_DETAIL, {"topicId": str(topic_id)}, "discussPostDetail")
    node = data.get("ugcArticleDiscussionArticle")
    if not node:
        return None
    # detail call returns body in `content` — stash it on the node so the
    # caller can pull it through _post_node_to_dataclass + a second read.
    post = _post_node_to_dataclass(node)
    post.summary = node.get("content") or node.get("summary") or post.summary
    return post


def fetch_comments(topic_id: int, *, order: str = "best", limit: int = 20) -> tuple[int, list[Comment]]:
    per_page = min(limit, 50)
    ord_v = COMMENT_ORDER_MAP.get(order, "best")
    data = gql(
        Q_DISCUSS_COMMENTS,
        {"topicId": int(topic_id), "pageNo": 1, "numPerPage": per_page, "orderBy": ord_v},
        "questionDiscussComments",
    )
    node = data.get("topicComments") or {}
    total = node.get("totalNum", 0) or 0
    comments: list[Comment] = []
    for c in (node.get("data") or [])[:limit]:
        post = c.get("post") or {}
        author = post.get("author") or {}
        comments.append(
            Comment(
                id=c.get("id", 0),
                author=author.get("username", "?"),
                content=post.get("content", ""),
                created_at=_unix_to_iso(post.get("creationDate")),
                vote_count=post.get("voteCount", 0) or 0,
                num_children=c.get("numChildren", 0) or 0,
                pinned=bool(c.get("pinned")),
            )
        )
    return total, comments


def fetch_hot_tags() -> list[dict]:
    data = gql(Q_DISCUSS_HOT_TAGS, {}, "discussExploreItems")
    out = []
    for t in data.get("ugcArticleDiscussionHotTags") or []:
        discussions = t.get("discussions") or []
        out.append(
            {
                "id": t.get("id"),
                "name": t.get("name"),
                "slug": t.get("slug"),
                "discussion_count": len(discussions),
                "discussions": discussions,
            }
        )
    return out


# ---------------------------------------------------------------------------
# GraphQL: company list
# ---------------------------------------------------------------------------

Q_FAVORITE_DETAIL = """
query favoriteDetailV2ForCompany($favoriteSlug: String!) {
  favoriteDetailV2(favoriteSlug: $favoriteSlug) {
    name slug description questionNumber collectCount isPublicFavorite
    favoriteType lastModified: lastQuestionAddedAt
    creator { realName userSlug }
    positionRoleTags { name slug }
    generatedFavoritesInfo {
      defaultFavoriteSlug
      categoriesToSlugs { categoryName favoriteSlug displayName }
    }
  }
}
"""


def fetch_company(slug: str) -> CompanyInfo:
    data = gql(Q_FAVORITE_DETAIL, {"favoriteSlug": slug}, "favoriteDetailV2ForCompany")
    node = data.get("favoriteDetailV2")
    if not node:
        raise LCNotFound(f"no company list with slug {slug!r}")
    creator = node.get("creator") or {}
    gen = (node.get("generatedFavoritesInfo") or {}).get("categoriesToSlugs") or []
    return CompanyInfo(
        slug=node.get("slug", slug),
        name=node.get("name", ""),
        description=node.get("description") or "",
        question_count=node.get("questionNumber", 0) or 0,
        collect_count=node.get("collectCount", 0) or 0,
        is_public=bool(node.get("isPublicFavorite")),
        favorite_type=node.get("favoriteType", ""),
        last_modified=node.get("lastModified", "") or "",
        creator=creator.get("realName") or creator.get("userSlug") or "",
        generated_slugs=[
            {
                "category": g.get("categoryName"),
                "slug": g.get("favoriteSlug"),
                "label": g.get("displayName"),
            }
            for g in gen
        ],
        position_role_tags=[
            {"name": t["name"], "slug": t["slug"]}
            for t in (node.get("positionRoleTags") or [])
        ],
        url=f"{BASE}/company/{slug}/",
    )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _unix_to_iso(ts) -> str:
    if not ts:
        return ""
    try:
        return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).isoformat()
    except Exception:
        return str(ts)


def html_to_text(s: str) -> str:
    """Convert LeetCode question HTML to readable plaintext / lightweight markdown."""
    if not s:
        return ""
    # Normalize line breaks first
    s = s.replace("\r\n", "\n")
    # Convert common tags
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>", "\n\n", s, flags=re.I)
    s = re.sub(r"<p[^>]*>", "", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    s = re.sub(r"</li>", "\n", s, flags=re.I)
    s = re.sub(r"</?ul[^>]*>|</?ol[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<sup[^>]*>(.*?)</sup>", r"^\1", s, flags=re.I | re.S)
    s = re.sub(r"<sub[^>]*>(.*?)</sub>", r"_\1", s, flags=re.I | re.S)
    s = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", s, flags=re.I | re.S)
    s = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", s, flags=re.I | re.S)
    s = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", s, flags=re.I | re.S)
    s = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", s, flags=re.I | re.S)
    s = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", s, flags=re.I | re.S)
    s = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", s, flags=re.I | re.S)
    s = re.sub(r"<img[^>]*alt=\"([^\"]*)\"[^>]*>", r"[image: \1]", s, flags=re.I)
    s = re.sub(r"<img[^>]*>", "[image]", s, flags=re.I)
    # Strip any remaining tags
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    # Collapse whitespace
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _fmt_int(n) -> str:
    if n is None:
        return "?"
    n = int(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _fmt_pct(x) -> str:
    return "?" if x is None else f"{x*100:.1f}%"


def _fmt_dt(s: str) -> str:
    if not s:
        return ""
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s


def _wrap(s: str, width: int = 100, indent: str = "") -> str:
    import textwrap

    lines = []
    for para in s.splitlines():
        if not para.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(para, width=width, initial_indent=indent, subsequent_indent=indent)
        lines.extend(wrapped or [indent + para])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Renderers (pretty text output)
# ---------------------------------------------------------------------------


def render_problem_row(p: Problem) -> str:
    paid = " 🔒" if p.paid_only else ""
    return (
        f"#{p.frontend_id:>5}  [{p.difficulty:<6}] {p.title}{paid}\n"
        f"        ac {_fmt_pct(p.ac_rate)} ({_fmt_int(p.total_accepted)}/{_fmt_int(p.total_submitted)})  "
        f"{p.url}"
    )


def render_problem_detail(d: ProblemDetail) -> str:
    p = d.problem
    out = []
    out.append(f"# #{p.frontend_id} — {p.title}  [{p.difficulty}]")
    out.append(p.url)
    out.append("")
    bits = []
    if d.likes is not None:
        bits.append(f"👍 {_fmt_int(d.likes)}")
    if d.dislikes is not None:
        bits.append(f"👎 {_fmt_int(d.dislikes)}")
    if p.ac_rate is not None:
        bits.append(f"AC {_fmt_pct(p.ac_rate)}")
    if p.paid_only:
        bits.append("🔒 premium")
    if bits:
        out.append("  ".join(bits))
    if p.tags:
        out.append("Tags: " + ", ".join(p.tags))
    out.append("")
    out.append(d.content_text or "(no content)")
    if d.hints:
        out.append("")
        out.append("## Hints")
        for i, h in enumerate(d.hints, 1):
            out.append(f"{i}. {html_to_text(h)}")
    if d.example_testcases:
        out.append("")
        out.append("## Example test cases")
        out.append("```")
        out.append(d.example_testcases)
        out.append("```")
    if d.code_snippets:
        langs = ", ".join(s.lang for s in d.code_snippets)
        out.append("")
        out.append(f"## Code snippets available: {langs}")
    if d.similar_questions:
        out.append("")
        out.append("## Similar questions")
        for sq in d.similar_questions[:8]:
            out.append(f"  - [{sq.get('difficulty','?')}] {sq.get('title')} (/problems/{sq.get('titleSlug')}/)")
    return "\n".join(out)


def render_discuss_post(p: DiscussPost, *, with_body: bool = False) -> str:
    head = f"#{p.topic_id}  {p.title}"
    meta = (
        f"  by {p.author or '?'}  "
        f"♥ {p.upvotes}  💬 {p.comment_count}  👁 {_fmt_int(p.hit_count)}  "
        f"{_fmt_dt(p.created_at)}"
    )
    tags = ""
    if p.tags:
        tag_strs = []
        for t in p.tags:
            tag_strs.append(f"#{t['slug']}" + ("*" if t.get("type") == "COMPANY" else ""))
        tags = "  " + " ".join(tag_strs)
    body = ""
    if with_body and p.summary:
        body = "\n" + _wrap(p.summary, indent="    ")
    return f"{head}\n{meta}{tags}\n  {p.url}{body}"


def render_comment(c: Comment) -> str:
    pin = " 📌" if c.pinned else ""
    head = f"  • {c.author}{pin}  ♥ {c.vote_count}  {_fmt_dt(c.created_at)}"
    body = _wrap(c.content, indent="    ")
    rep = f"\n    ↳ {c.num_children} repl{'y' if c.num_children == 1 else 'ies'}" if c.num_children else ""
    return f"{head}\n{body}{rep}"


def render_article(a: Article) -> str:
    out = [render_discuss_post(a.post, with_body=False)]
    out.append("")
    out.append(a.content if a.content else "(no body)")
    out.append("")
    if a.comments:
        out.append(f"--- comments ({len(a.comments)}/{a.total_comment_count}) ---")
        for c in a.comments:
            out.append(render_comment(c))
            out.append("")
    else:
        out.append("(no comments)")
    return "\n".join(out)


def render_company(c: CompanyInfo) -> str:
    out = [
        f"# {c.name}  ({c.slug})",
        c.url,
        f"{c.question_count} questions  •  {c.collect_count} collected  •  type: {c.favorite_type}",
        f"last modified {_fmt_dt(c.last_modified)}  •  curated by {c.creator}",
    ]
    if c.description:
        out.append("")
        out.append(c.description)
    if c.position_role_tags:
        out.append("")
        out.append("Roles: " + ", ".join(t["name"] for t in c.position_role_tags))
    if c.generated_slugs:
        out.append("")
        out.append("Sub-lists (require LeetCode premium to view problems):")
        for g in c.generated_slugs:
            out.append(f"  - {g['label']:<20s}  slug={g['slug']}")
    out.append("")
    out.append(
        "Note: company question lists are paywalled by LeetCode. "
        "This call returns metadata only — to see the actual problems, open the URL with a premium account."
    )
    return "\n".join(out)


def render_tags(tags: list[dict]) -> str:
    lines = []
    for t in tags:
        if t["discussion_count"] == 0:
            continue
        lines.append(f"#{t['slug']:<25s} ({t['discussion_count']} hot)  {t['name']}")
        for d in t["discussions"][:3]:
            lines.append(f"    #{d['topicId']}  {d['title']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------------


def export_problem(d: ProblemDetail, fmt: str) -> str:
    if fmt == "json":
        out = asdict(d)
        return json.dumps(out, indent=2)
    p = d.problem
    out = [f"# #{p.frontend_id} — {p.title}", "", f"- URL: {p.url}", f"- Difficulty: {p.difficulty}"]
    if p.tags:
        out.append(f"- Tags: {', '.join(p.tags)}")
    if d.likes is not None or d.dislikes is not None:
        out.append(f"- Likes: {d.likes}  Dislikes: {d.dislikes}")
    if p.ac_rate is not None:
        out.append(f"- AC rate: {_fmt_pct(p.ac_rate)}")
    out.append("")
    out.append("## Problem")
    out.append("")
    out.append(d.content_text)
    if d.hints:
        out.append("")
        out.append("## Hints")
        for h in d.hints:
            out.append(f"- {html_to_text(h)}")
    if d.example_testcases:
        out.append("")
        out.append("## Example testcases")
        out.append("```")
        out.append(d.example_testcases)
        out.append("```")
    if d.similar_questions:
        out.append("")
        out.append("## Similar questions")
        for sq in d.similar_questions:
            out.append(f"- [{sq.get('difficulty','?')}] {sq.get('title')} — /problems/{sq.get('titleSlug')}/")
    if d.code_snippets:
        out.append("")
        out.append("## Code snippets")
        for s in d.code_snippets:
            out.append(f"### {s.lang}")
            out.append(f"```{s.lang_slug}")
            out.append(s.code)
            out.append("```")
            out.append("")
    return "\n".join(out)


def export_article(a: Article, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(asdict(a), indent=2)
    p = a.post
    out = [
        f"# {p.title}",
        "",
        f"- URL: {p.url}",
        f"- Author: {p.author}",
        f"- Posted: {_fmt_dt(p.created_at)}",
        f"- ♥ {p.upvotes}  💬 {p.comment_count}  👁 {_fmt_int(p.hit_count)}",
    ]
    if p.tags:
        out.append(f"- Tags: " + ", ".join(f"{t['name']}" for t in p.tags))
    out.append("")
    out.append("## Body")
    out.append("")
    out.append(a.content or "(no body)")
    out.append("")
    out.append(f"## Comments ({len(a.comments)}/{a.total_comment_count})")
    out.append("")
    for c in a.comments:
        out.append(f"### {c.author}  ({_fmt_dt(c.created_at)})  ♥ {c.vote_count}")
        out.append("")
        out.append(c.content)
        if c.num_children:
            out.append("")
            out.append(f"_({c.num_children} more replies — open the URL to read)_")
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _print_json(obj):
    print(json.dumps(obj, indent=2, default=str))


def cmd_daily(args):
    date, p = fetch_daily()
    if args.json:
        _print_json({"date": date, "problem": asdict(p)})
        return 0
    print(f"Daily challenge for {date}")
    print(render_problem_row(p))
    return 0


def cmd_problem(args):
    slug = _slug_from_arg(args.target)
    d = fetch_problem_detail(slug)
    if args.json:
        _print_json(asdict(d))
        return 0
    print(render_problem_detail(d))
    return 0


def cmd_search(args):
    results = search_problems(
        args.query,
        difficulty=args.difficulty,
        paid=(True if args.paid else False if args.free else None),
        limit=args.limit,
    )
    if args.json:
        _print_json([asdict(r) for r in results])
        return 0
    if not results:
        print(f"No problems matching {args.query!r}", file=sys.stderr)
        return 2
    for r in results:
        print(render_problem_row(r))
        print()
    return 0


def cmd_list(args):
    results = search_problems(
        "",
        difficulty=args.difficulty,
        paid=(True if args.paid else False if args.free else None),
        limit=args.limit,
    )
    if args.json:
        _print_json([asdict(r) for r in results])
        return 0
    for r in results:
        print(render_problem_row(r))
        print()
    return 0


def cmd_discuss(args):
    total, has_more, posts = search_discuss(
        args.query,
        tag_slugs=args.tag,
        order=args.order,
        first=args.limit,
    )
    if args.json:
        _print_json({"total": total, "has_more": has_more, "posts": [asdict(p) for p in posts]})
        return 0
    if not posts:
        print(f"No discussion posts matching {args.query!r}", file=sys.stderr)
        return 2
    print(f"-- {len(posts)} of {total} posts (order={args.order})")
    print()
    for p in posts:
        print(render_discuss_post(p, with_body=True))
        print()
    return 0


def cmd_feed(args):
    tags = [args.tag] if args.tag else []
    total, has_more, posts = search_discuss(
        "",
        tag_slugs=tags,
        order=args.order,
        first=args.limit,
    )
    if args.json:
        _print_json({"total": total, "has_more": has_more, "posts": [asdict(p) for p in posts]})
        return 0
    label = f"#{args.tag}" if args.tag else "all"
    print(f"-- {label} discussion feed ({len(posts)} of {total}, order={args.order})")
    print()
    for p in posts:
        print(render_discuss_post(p, with_body=False))
        print()
    return 0


def cmd_read(args):
    tid = _topic_id_from_arg(args.target)
    post = fetch_post_detail(tid)
    if not post:
        raise LCNotFound(f"no discuss post with topicId {tid}")
    total, comments = fetch_comments(tid, order=args.order, limit=args.limit)
    body = post.summary
    # The detail endpoint stuffed content into summary above. Build Article:
    a = Article(post=post, content=body, comments=comments, total_comment_count=total)
    # Reset summary on post (so JSON output is sensible) — drop body from there
    post_no_body = dataclasses.replace(post, summary="")
    a_no_dupe = Article(post=post_no_body, content=body, comments=comments, total_comment_count=total)
    if args.json:
        _print_json(asdict(a_no_dupe))
        return 0
    print(render_article(a_no_dupe))
    return 0


def cmd_comments(args):
    tid = _topic_id_from_arg(args.target)
    total, comments = fetch_comments(tid, order=args.order, limit=args.limit)
    if args.json:
        _print_json({"total": total, "comments": [asdict(c) for c in comments]})
        return 0
    print(f"-- {len(comments)} of {total} comments (order={args.order})")
    print()
    for c in comments:
        print(render_comment(c))
        print()
    return 0


def cmd_company(args):
    c = fetch_company(args.slug)
    if args.json:
        _print_json(asdict(c))
        return 0
    print(render_company(c))
    return 0


def cmd_tags(args):
    tags = fetch_hot_tags()
    if args.json:
        _print_json(tags)
        return 0
    print(render_tags(tags))
    return 0


def cmd_export(args):
    tid = _topic_id_from_arg(args.target)
    post = fetch_post_detail(tid)
    if not post:
        raise LCNotFound(f"no discuss post with topicId {tid}")
    body = post.summary
    total, comments = fetch_comments(tid, order=args.order, limit=args.limit)
    post_no_body = dataclasses.replace(post, summary="")
    a = Article(post=post_no_body, content=body, comments=comments, total_comment_count=total)
    print(export_article(a, args.format))
    return 0


def cmd_export_problem(args):
    slug = _slug_from_arg(args.target)
    d = fetch_problem_detail(slug)
    print(export_problem(d, args.format))
    return 0


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lcsearch", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp, *, limit_default=20, with_order=False):
        sp.add_argument("--json", action="store_true", help="emit JSON")
        sp.add_argument("--limit", type=int, default=limit_default, help="max items")
        sp.add_argument("-v", "--verbose", action="store_true", help="log fetched URLs")
        if with_order:
            sp.add_argument(
                "--order",
                choices=["hot", "recent", "votes"],
                default="hot",
                help="sort order for discuss endpoints",
            )

    sp_daily = sub.add_parser("daily", help="today's daily challenge")
    add_common(sp_daily)
    sp_daily.set_defaults(func=cmd_daily)

    sp_problem = sub.add_parser("problem", help="full problem detail")
    sp_problem.add_argument("target", help="slug, frontend id, or /problems/<slug>/ URL")
    add_common(sp_problem)
    sp_problem.set_defaults(func=cmd_problem)

    sp_search = sub.add_parser("search", help="search problem catalog")
    sp_search.add_argument("query", help="substring or frontend id")
    sp_search.add_argument("--difficulty", choices=["Easy", "Medium", "Hard"])
    sp_search.add_argument("--paid", action="store_true", help="only paid problems")
    sp_search.add_argument("--free", action="store_true", help="only free problems")
    add_common(sp_search)
    sp_search.set_defaults(func=cmd_search)

    sp_list = sub.add_parser("list", help="list problems with filters (no keyword)")
    sp_list.add_argument("--difficulty", choices=["Easy", "Medium", "Hard"])
    sp_list.add_argument("--paid", action="store_true")
    sp_list.add_argument("--free", action="store_true")
    add_common(sp_list, limit_default=50)
    sp_list.set_defaults(func=cmd_list)

    sp_discuss = sub.add_parser("discuss", help="search discuss posts")
    sp_discuss.add_argument("query")
    sp_discuss.add_argument("--tag", action="append", help="restrict to a tag slug (repeatable)")
    add_common(sp_discuss, with_order=True)
    sp_discuss.set_defaults(func=cmd_discuss)

    sp_feed = sub.add_parser("feed", help="discuss feed (optionally tag-filtered)")
    sp_feed.add_argument("tag", nargs="?", help="tag slug, e.g. google, interview, compensation")
    add_common(sp_feed, with_order=True)
    sp_feed.set_defaults(func=cmd_feed)

    sp_read = sub.add_parser("read", help="full discuss post + comments")
    sp_read.add_argument("target", help="numeric topicId or /discuss/topic/<id> URL")
    add_common(sp_read, with_order=True)
    sp_read.set_defaults(func=cmd_read)

    sp_com = sub.add_parser("comments", help="comments on a discuss post")
    sp_com.add_argument("target")
    add_common(sp_com, with_order=True)
    sp_com.set_defaults(func=cmd_comments)

    sp_company = sub.add_parser("company", help="company list metadata")
    sp_company.add_argument("slug", help="company list slug, e.g. waymo, google, meta")
    add_common(sp_company)
    sp_company.set_defaults(func=cmd_company)

    sp_tags = sub.add_parser("tags", help="hot discuss tags")
    add_common(sp_tags)
    sp_tags.set_defaults(func=cmd_tags)

    sp_export = sub.add_parser("export", help="export discuss post + comments")
    sp_export.add_argument("target")
    sp_export.add_argument("--format", choices=["md", "json"], default="md")
    add_common(sp_export, with_order=True)
    sp_export.set_defaults(func=cmd_export)

    sp_ep = sub.add_parser("export-problem", help="export problem to markdown/json")
    sp_ep.add_argument("target")
    sp_ep.add_argument("--format", choices=["md", "json"], default="md")
    add_common(sp_ep)
    sp_ep.set_defaults(func=cmd_export_problem)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    global _verbose
    _verbose = bool(getattr(args, "verbose", False))
    try:
        return args.func(args) or 0
    except LCNotFound as e:
        print(f"not found: {e}", file=sys.stderr)
        return 2
    except LCError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
