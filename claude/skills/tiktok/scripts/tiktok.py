#!/usr/bin/env python3
"""TikTok Search: search videos and users."""

import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from tiktok_common import (
    tiktok_session, extract_video_data, enrich_video,
    format_video_results, output_results, add_common_args, add_video_args,
)

SEARCH_URL = "https://www.tiktok.com/api/search/item/full/"


async def search_videos(query, count=10, fetch_transcripts=True, fetch_details=False):
    """Search TikTok videos and return enriched results."""
    async with tiktok_session() as api:
        all_results = []
        cursor = 0
        remaining = count

        while remaining > 0:
            batch = min(remaining, 20)
            resp = await api.make_request(url=SEARCH_URL, params={
                "keyword": query,
                "count": batch,
                "cursor": cursor,
                "source": "search_video",
            })

            items = resp.get("item_list", [])
            if not items:
                break

            for video in items:
                data = extract_video_data(video)
                data = await enrich_video(
                    data, api=api,
                    fetch_transcripts=fetch_transcripts,
                    fetch_details=fetch_details,
                )
                all_results.append(data)

            cursor = resp.get("cursor", cursor + batch)
            if not resp.get("has_more", False):
                break
            remaining -= len(items)

        return all_results


async def search_users(query, count=10):
    """Search TikTok users."""
    async with tiktok_session() as api:
        results = []
        async for user in api.search.users(query, count=count):
            info = user.as_dict if hasattr(user, 'as_dict') else {}
            results.append({
                "username": info.get("uniqueId", getattr(user, 'username', '')),
                "nickname": info.get("nickname", ''),
                "verified": info.get("verified", False),
                "followers": info.get("followerCount", 0),
                "following": info.get("followingCount", 0),
                "likes": info.get("heartCount", info.get("heart", 0)),
                "videos": info.get("videoCount", 0),
                "bio": info.get("signature", ""),
                "url": f"https://www.tiktok.com/@{info.get('uniqueId', getattr(user, 'username', ''))}",
            })
        return results


def format_user_results(results, verbose=False):
    """Format user search results for human-readable output."""
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"\n{'='*60}")
        lines.append(f"{i}. @{r['username']} ({r['nickname']})")
        verified = " [verified]" if r["verified"] else ""
        lines.append(f"   {r['url']}{verified}")
        lines.append(f"   Followers: {r['followers']:,} | Following: {r['following']:,} | Likes: {r['likes']:,} | Videos: {r['videos']:,}")
        if r["bio"]:
            bio = r["bio"][:200] if not verbose else r["bio"]
            lines.append(f"   Bio: {bio}")
    return "\n".join(lines)


async def main():
    # Check if first arg is a known subcommand; if not, default to "videos"
    known = {"videos", "users"}
    argv = sys.argv[1:]
    if argv and argv[0] not in known and not argv[0].startswith("-"):
        argv = ["videos"] + argv

    parser = argparse.ArgumentParser(description="Search TikTok videos and users")
    subparsers = parser.add_subparsers(dest="command", help="Search type")

    # videos subcommand (default)
    vp = subparsers.add_parser("videos", help="Search videos (default)")
    vp.add_argument("query", help="Search query")
    add_common_args(vp)
    add_video_args(vp)

    # users subcommand
    up = subparsers.add_parser("users", help="Search users")
    up.add_argument("query", help="Search query")
    add_common_args(up)

    args = parser.parse_args(argv)

    if args.command == "videos":
        results = await search_videos(
            query=args.query,
            count=args.count,
            fetch_transcripts=not getattr(args, 'no_transcripts', False),
            fetch_details=getattr(args, 'details', False),
        )
        print(f"\nFound {len(results)} video results for: {args.query}")
        output_results(results, args, format_fn=format_video_results)
    elif args.command == "users":
        results = await search_users(query=args.query, count=args.count)
        print(f"\nFound {len(results)} user results for: {args.query}")
        output_results(results, args, format_fn=format_user_results)


if __name__ == "__main__":
    asyncio.run(main())
