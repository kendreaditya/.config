#!/usr/bin/env python3
"""TikTok User: fetch user info, videos, and liked videos."""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tiktok_common import (
    tiktok_session, extract_video_data, enrich_video,
    format_video_results, output_results, add_common_args, add_video_args,
)


async def user_info(username):
    """Get user profile information."""
    async with tiktok_session() as api:
        user = api.user(username=username)
        data = await user.info()
        info = data.get("userInfo", data)
        u = info.get("user", info)
        stats = info.get("stats", {})
        return {
            "username": u.get("uniqueId", username),
            "nickname": u.get("nickname", ""),
            "verified": u.get("verified", False),
            "bio": u.get("signature", ""),
            "followers": stats.get("followerCount", 0),
            "following": stats.get("followingCount", 0),
            "likes": stats.get("heartCount", stats.get("heart", 0)),
            "videos": stats.get("videoCount", 0),
            "url": f"https://www.tiktok.com/@{u.get('uniqueId', username)}",
            "private": u.get("privateAccount", False),
            "created": u.get("createTime", 0),
        }


async def user_videos(username, count=10, fetch_transcripts=True, fetch_details=False):
    """Get a user's posted videos."""
    async with tiktok_session() as api:
        user = api.user(username=username)
        results = []
        async for video in user.videos(count=count):
            raw = video.as_dict if hasattr(video, 'as_dict') else video
            data = extract_video_data(raw)
            data = await enrich_video(
                data, api=api,
                fetch_transcripts=fetch_transcripts,
                fetch_details=fetch_details,
            )
            results.append(data)
        return results


async def user_liked(username, count=10, fetch_transcripts=True, fetch_details=False):
    """Get a user's liked videos (if public)."""
    async with tiktok_session() as api:
        user = api.user(username=username)
        results = []
        async for video in user.liked(count=count):
            raw = video.as_dict if hasattr(video, 'as_dict') else video
            data = extract_video_data(raw)
            data = await enrich_video(
                data, api=api,
                fetch_transcripts=fetch_transcripts,
                fetch_details=fetch_details,
            )
            results.append(data)
        return results


def format_user_info(result, verbose=False):
    """Format user info for human-readable output."""
    r = result
    lines = [
        f"\n@{r['username']} ({r['nickname']})",
        f"{'='*60}",
        f"URL: {r['url']}",
        f"Verified: {r['verified']}",
        f"Private: {r['private']}",
        f"Followers: {r['followers']:,} | Following: {r['following']:,}",
        f"Likes: {r['likes']:,} | Videos: {r['videos']:,}",
    ]
    if r["bio"]:
        lines.append(f"Bio: {r['bio']}")
    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="TikTok user data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ip = subparsers.add_parser("info", help="Get user profile info")
    ip.add_argument("username", help="TikTok username (without @)")
    ip.add_argument("--json", action="store_true", dest="json_output")
    ip.add_argument("-o", "--output", help="Save JSON to file")

    vp = subparsers.add_parser("videos", help="Get user's videos")
    vp.add_argument("username", help="TikTok username")
    add_common_args(vp)
    add_video_args(vp)

    lp = subparsers.add_parser("liked", help="Get user's liked videos (if public)")
    lp.add_argument("username", help="TikTok username")
    add_common_args(lp)
    add_video_args(lp)

    args = parser.parse_args()

    if args.command == "info":
        result = await user_info(args.username)
        if getattr(args, 'json_output', False) or getattr(args, 'output', None):
            import json
            json_str = json.dumps(result, indent=2, ensure_ascii=False, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(json_str)
                print(f"Saved to {args.output}")
            if getattr(args, 'json_output', False):
                print(json_str)
        else:
            print(format_user_info(result))
    elif args.command == "videos":
        results = await user_videos(
            args.username, count=args.count,
            fetch_transcripts=not getattr(args, 'no_transcripts', False),
            fetch_details=getattr(args, 'details', False),
        )
        print(f"\nFound {len(results)} videos from @{args.username}")
        output_results(results, args, format_fn=format_video_results)
    elif args.command == "liked":
        results = await user_liked(
            args.username, count=args.count,
            fetch_transcripts=not getattr(args, 'no_transcripts', False),
            fetch_details=getattr(args, 'details', False),
        )
        print(f"\nFound {len(results)} liked videos from @{args.username}")
        output_results(results, args, format_fn=format_video_results)


if __name__ == "__main__":
    asyncio.run(main())
