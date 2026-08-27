#!/usr/bin/env python3
"""TikTok Video: fetch video info, comments, and related videos."""

import argparse
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tiktok_common import (
    tiktok_session, extract_video_data, enrich_video,
    format_video_results, output_results, add_common_args, add_video_args,
)


def parse_video_id(video_ref):
    """Extract video ID from a URL or raw ID string."""
    m = re.search(r'/video/(\d+)', video_ref)
    if m:
        return m.group(1)
    if video_ref.strip().isdigit():
        return video_ref.strip()
    return video_ref


async def video_info(video_id, fetch_transcripts=True):
    """Get detailed video information."""
    async with tiktok_session() as api:
        resp = await api.make_request(
            url="https://www.tiktok.com/api/item/detail/",
            params={"itemId": video_id},
        )
        if "itemInfo" not in resp:
            print(f"Error: could not fetch video {video_id}", file=sys.stderr)
            sys.exit(1)
        item = resp["itemInfo"]["itemStruct"]
        data = extract_video_data(item)
        data = await enrich_video(data, api=api, fetch_transcripts=fetch_transcripts)
        return data


async def video_comments(video_id, count=20):
    """Get comments on a video."""
    async with tiktok_session() as api:
        video = api.video(id=video_id)
        results = []
        async for comment in video.comments(count=count):
            raw = comment.as_dict if hasattr(comment, 'as_dict') else comment
            results.append({
                "id": raw.get("cid", raw.get("id", "")),
                "text": raw.get("text", ""),
                "author": raw.get("user", {}).get("uniqueId", raw.get("user", {}).get("unique_id", "")),
                "likes": raw.get("digg_count", raw.get("diggCount", 0)),
                "replies": raw.get("reply_comment_total", raw.get("replyCommentTotal", 0)),
                "create_time": raw.get("create_time", raw.get("createTime", 0)),
            })
        return results


async def video_related(video_id, count=10, fetch_transcripts=True):
    """Get related/recommended videos."""
    async with tiktok_session() as api:
        video = api.video(id=video_id)
        results = []
        async for vid in video.related_videos(count=count):
            raw = vid.as_dict if hasattr(vid, 'as_dict') else vid
            data = extract_video_data(raw)
            data = await enrich_video(data, api=api, fetch_transcripts=fetch_transcripts)
            results.append(data)
        return results


def format_comments(results, verbose=False):
    """Format comments for human-readable output."""
    lines = []
    for i, c in enumerate(results, 1):
        lines.append(f"\n{i}. @{c['author']} ({c['likes']:,} likes, {c['replies']} replies)")
        text = c['text'] if verbose else c['text'][:300]
        lines.append(f"   {text}")
    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="TikTok video data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ip = subparsers.add_parser("info", help="Get video details")
    ip.add_argument("video", help="Video ID or URL")
    ip.add_argument("--json", action="store_true", dest="json_output")
    ip.add_argument("--no-transcripts", action="store_true")
    ip.add_argument("-o", "--output", help="Save JSON to file")

    cp = subparsers.add_parser("comments", help="Get video comments")
    cp.add_argument("video", help="Video ID or URL")
    add_common_args(cp)

    rp = subparsers.add_parser("related", help="Get related videos")
    rp.add_argument("video", help="Video ID or URL")
    add_common_args(rp)
    add_video_args(rp)

    args = parser.parse_args()
    video_id = parse_video_id(args.video)

    if args.command == "info":
        result = await video_info(video_id, fetch_transcripts=not getattr(args, 'no_transcripts', False))
        if getattr(args, 'json_output', False) or getattr(args, 'output', None):
            json_str = json.dumps(result, indent=2, ensure_ascii=False, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(json_str)
                print(f"Saved to {args.output}")
            if getattr(args, 'json_output', False):
                print(json_str)
        else:
            print(format_video_results([result], verbose=True))
    elif args.command == "comments":
        results = await video_comments(video_id, count=args.count)
        print(f"\nFound {len(results)} comments on video {video_id}")
        output_results(results, args, format_fn=format_comments)
    elif args.command == "related":
        results = await video_related(
            video_id, count=args.count,
            fetch_transcripts=not getattr(args, 'no_transcripts', False),
        )
        print(f"\nFound {len(results)} related videos")
        output_results(results, args, format_fn=format_video_results)


if __name__ == "__main__":
    asyncio.run(main())
