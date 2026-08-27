#!/usr/bin/env python3
"""TikTok Trending: fetch trending/FYP videos."""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tiktok_common import (
    tiktok_session, extract_video_data, enrich_video,
    format_video_results, output_results, add_common_args, add_video_args,
)


async def trending_videos(count=10, fetch_transcripts=True, fetch_details=False):
    """Get trending videos."""
    async with tiktok_session() as api:
        results = []
        async for video in api.trending.videos(count=count):
            raw = video.as_dict if hasattr(video, 'as_dict') else video
            data = extract_video_data(raw)
            data = await enrich_video(
                data, api=api,
                fetch_transcripts=fetch_transcripts,
                fetch_details=fetch_details,
            )
            results.append(data)
        return results


async def main():
    parser = argparse.ArgumentParser(description="TikTok trending videos")
    add_common_args(parser)
    add_video_args(parser)
    args = parser.parse_args()

    results = await trending_videos(
        count=args.count,
        fetch_transcripts=not getattr(args, 'no_transcripts', False),
        fetch_details=getattr(args, 'details', False),
    )
    print(f"\nFound {len(results)} trending videos")
    output_results(results, args, format_fn=format_video_results)


if __name__ == "__main__":
    asyncio.run(main())
