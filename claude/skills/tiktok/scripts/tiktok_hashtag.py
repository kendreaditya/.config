#!/usr/bin/env python3
"""TikTok Hashtag: fetch hashtag info and videos."""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tiktok_common import (
    tiktok_session, extract_video_data, enrich_video,
    format_video_results, output_results, add_common_args, add_video_args,
)


async def hashtag_info(name):
    """Get hashtag/challenge statistics."""
    async with tiktok_session() as api:
        tag = api.hashtag(name=name)
        data = await tag.info()
        ch = data.get("challengeInfo", data)
        challenge = ch.get("challenge", ch)
        stats = ch.get("stats", {})
        return {
            "id": challenge.get("id", ""),
            "name": challenge.get("title", name),
            "description": challenge.get("desc", ""),
            "views": stats.get("viewCount", stats.get("videoCount", 0)),
            "videos": stats.get("videoCount", 0),
            "url": f"https://www.tiktok.com/tag/{name}",
        }


async def hashtag_videos(name, count=10, fetch_transcripts=True, fetch_details=False):
    """Get videos using a hashtag."""
    async with tiktok_session() as api:
        tag = api.hashtag(name=name)
        results = []
        async for video in tag.videos(count=count):
            raw = video.as_dict if hasattr(video, 'as_dict') else video
            data = extract_video_data(raw)
            data = await enrich_video(
                data, api=api,
                fetch_transcripts=fetch_transcripts,
                fetch_details=fetch_details,
            )
            results.append(data)
        return results


def format_hashtag_info(result, verbose=False):
    """Format hashtag info for human-readable output."""
    r = result
    lines = [
        f"\n#{r['name']}",
        f"{'='*60}",
        f"URL: {r['url']}",
        f"Views: {r['views']:,} | Videos: {r['videos']:,}",
    ]
    if r["description"]:
        lines.append(f"Description: {r['description']}")
    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="TikTok hashtag data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ip = subparsers.add_parser("info", help="Get hashtag stats")
    ip.add_argument("name", help="Hashtag name (without #)")
    ip.add_argument("--json", action="store_true", dest="json_output")
    ip.add_argument("-o", "--output", help="Save JSON to file")

    vp = subparsers.add_parser("videos", help="Get videos with hashtag")
    vp.add_argument("name", help="Hashtag name (without #)")
    add_common_args(vp)
    add_video_args(vp)

    args = parser.parse_args()

    if args.command == "info":
        result = await hashtag_info(args.name)
        if getattr(args, 'json_output', False) or getattr(args, 'output', None):
            json_str = json.dumps(result, indent=2, ensure_ascii=False, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(json_str)
                print(f"Saved to {args.output}")
            if getattr(args, 'json_output', False):
                print(json_str)
        else:
            print(format_hashtag_info(result))
    elif args.command == "videos":
        results = await hashtag_videos(
            args.name, count=args.count,
            fetch_transcripts=not getattr(args, 'no_transcripts', False),
            fetch_details=getattr(args, 'details', False),
        )
        print(f"\nFound {len(results)} videos for #{args.name}")
        output_results(results, args, format_fn=format_video_results)


if __name__ == "__main__":
    asyncio.run(main())
