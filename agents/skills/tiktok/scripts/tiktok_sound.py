#!/usr/bin/env python3
"""TikTok Sound: fetch sound/music info and videos using a sound."""

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


async def sound_info(sound_id):
    """Get sound/music metadata."""
    async with tiktok_session() as api:
        sound = api.sound(id=sound_id)
        data = await sound.info()
        music = data.get("musicInfo", data).get("music", data)
        stats = data.get("musicInfo", data).get("stats", {})
        return {
            "id": music.get("id", sound_id),
            "title": music.get("title", ""),
            "author": music.get("authorName", ""),
            "original": music.get("original", False),
            "duration": music.get("duration", 0),
            "videos": stats.get("videoCount", 0),
            "url": f"https://www.tiktok.com/music/-{sound_id}",
        }


async def sound_videos(sound_id, count=10, fetch_transcripts=True, fetch_details=False):
    """Get videos using a specific sound."""
    async with tiktok_session() as api:
        sound = api.sound(id=sound_id)
        results = []
        async for video in sound.videos(count=count):
            raw = video.as_dict if hasattr(video, 'as_dict') else video
            data = extract_video_data(raw)
            data = await enrich_video(
                data, api=api,
                fetch_transcripts=fetch_transcripts,
                fetch_details=fetch_details,
            )
            results.append(data)
        return results


def format_sound_info(result, verbose=False):
    """Format sound info for human-readable output."""
    r = result
    lines = [
        f"\n{r['title']} - {r['author']}",
        f"{'='*60}",
        f"URL: {r['url']}",
        f"Original: {r['original']} | Duration: {r['duration']}s",
        f"Videos using this sound: {r['videos']:,}",
    ]
    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="TikTok sound/music data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ip = subparsers.add_parser("info", help="Get sound metadata")
    ip.add_argument("sound_id", help="Sound/music ID")
    ip.add_argument("--json", action="store_true", dest="json_output")
    ip.add_argument("-o", "--output", help="Save JSON to file")

    vp = subparsers.add_parser("videos", help="Get videos using a sound")
    vp.add_argument("sound_id", help="Sound/music ID")
    add_common_args(vp)
    add_video_args(vp)

    args = parser.parse_args()

    if args.command == "info":
        result = await sound_info(args.sound_id)
        if getattr(args, 'json_output', False) or getattr(args, 'output', None):
            json_str = json.dumps(result, indent=2, ensure_ascii=False, default=str)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(json_str)
                print(f"Saved to {args.output}")
            if getattr(args, 'json_output', False):
                print(json_str)
        else:
            print(format_sound_info(result))
    elif args.command == "videos":
        results = await sound_videos(
            args.sound_id, count=args.count,
            fetch_transcripts=not getattr(args, 'no_transcripts', False),
            fetch_details=getattr(args, 'details', False),
        )
        print(f"\nFound {len(results)} videos using this sound")
        output_results(results, args, format_fn=format_video_results)


if __name__ == "__main__":
    asyncio.run(main())
