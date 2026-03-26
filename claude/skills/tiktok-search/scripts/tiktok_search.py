#!/usr/bin/env python3
"""TikTok Search: search videos and extract all available data sources."""

import argparse
import asyncio
import json
import os
import sys

import httpx
from TikTokApi import TikTokApi

SEARCH_URL = "https://www.tiktok.com/api/search/item/full/"
DETAIL_URL = "https://www.tiktok.com/api/item/detail/"


async def fetch_captions(caption_infos, subtitle_infos):
    """Download WebVTT captions from available URLs."""
    urls = []
    for ci in caption_infos:
        for u in ci.get("urlList", []):
            urls.append(u)
        if ci.get("url"):
            urls.append(ci["url"])
    for si in subtitle_infos:
        if si.get("Url"):
            urls.append(si["Url"])

    # Prefer CDN URLs
    cdn = [u for u in urls if "tiktokcdn" in u]
    aweme = [u for u in urls if "aweme" in u]
    ordered = cdn + aweme

    headers = {
        "Referer": "https://www.tiktok.com/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    async with httpx.AsyncClient() as client:
        for url in ordered:
            try:
                r = await client.get(url, headers=headers, follow_redirects=True, timeout=15)
                if r.status_code == 200 and ("WEBVTT" in r.text or "-->" in r.text):
                    return r.text
            except Exception:
                continue
    return None


def extract_video_data(video):
    """Extract all data sources from a single video result."""
    vid = video.get("video", {})
    cla = vid.get("claInfo", {})
    author = video.get("author", {})
    stats = video.get("statsV2", video.get("stats", {}))
    poi = video.get("poi", {})

    result = {
        "id": video.get("id"),
        "url": f"https://www.tiktok.com/@{author.get('uniqueId', '')}/video/{video.get('id', '')}",
        "description": video.get("desc", ""),
        "author": {
            "username": author.get("uniqueId", ""),
            "nickname": author.get("nickname", ""),
            "verified": author.get("verified", False),
            "followers": author.get("followerCount") or video.get("authorStats", {}).get("followerCount", 0),
        },
        "stats": {
            "views": stats.get("playCount", 0),
            "likes": stats.get("diggCount", 0),
            "comments": stats.get("commentCount", 0),
            "shares": stats.get("shareCount", 0),
            "saves": stats.get("collectCount", 0),
        },
        "duration_sec": vid.get("duration", 0),
        "create_time": video.get("createTime", 0),
        "hashtags": [c.get("title", "") for c in video.get("challenges", [])],
        "stickers_text": [],
        "location": None,
        "music": None,
        "caption_available": cla.get("enableAutoCaption", False),
        "transcript": None,
        "caption_language": None,
        # Raw fields for further inspection
        "_caption_infos": cla.get("captionInfos", []),
        "_subtitle_infos": vid.get("subtitleInfos", []),
    }

    # Stickers / on-screen text
    for sticker in video.get("stickersOnItem", []):
        texts = sticker.get("stickerText", [])
        if texts:
            result["stickers_text"].extend(texts)

    # POI / location
    if poi and poi.get("name"):
        result["location"] = {
            "name": poi.get("name", ""),
            "address": poi.get("address", ""),
            "city": poi.get("city", ""),
            "category": poi.get("category", ""),
            "type": poi.get("ttTypeNameTiny", ""),
        }

    # Music
    music = video.get("music", {})
    if music:
        result["music"] = {
            "title": music.get("title", ""),
            "author": music.get("authorName", ""),
            "original": music.get("original", False),
        }

    # Caption metadata
    for ci in cla.get("captionInfos", []):
        result["caption_language"] = ci.get("language", "")
        break

    return result


async def search_tiktok(query, count=10, fetch_transcripts=True, fetch_details=False):
    """Search TikTok and return enriched results."""
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[os.environ.get("ms_token", None)],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "chromium"),
        )

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

                # Try to get detail endpoint for richer data (subtitleInfos)
                if fetch_details:
                    try:
                        detail = await api.make_request(
                            url=DETAIL_URL, params={"itemId": data["id"]}
                        )
                        if "itemInfo" in detail:
                            item = detail["itemInfo"]["itemStruct"]
                            detail_data = extract_video_data(item)
                            # Merge: prefer detail for caption/subtitle fields
                            if detail_data["_caption_infos"]:
                                data["_caption_infos"] = detail_data["_caption_infos"]
                            if detail_data["_subtitle_infos"]:
                                data["_subtitle_infos"] = detail_data["_subtitle_infos"]
                            if detail_data["caption_available"]:
                                data["caption_available"] = True
                            # Merge stickers and location if missing
                            if not data["stickers_text"] and detail_data["stickers_text"]:
                                data["stickers_text"] = detail_data["stickers_text"]
                            if not data["location"] and detail_data["location"]:
                                data["location"] = detail_data["location"]
                    except Exception:
                        pass

                # Fetch transcripts
                if fetch_transcripts and (data["_caption_infos"] or data["_subtitle_infos"]):
                    transcript = await fetch_captions(
                        data["_caption_infos"], data["_subtitle_infos"]
                    )
                    if transcript:
                        data["transcript"] = transcript

                # Remove internal fields
                del data["_caption_infos"]
                del data["_subtitle_infos"]

                all_results.append(data)

            cursor = resp.get("cursor", cursor + batch)
            if not resp.get("has_more", False):
                break
            remaining -= len(items)

        return all_results


def format_results(results, verbose=False):
    """Format results for human-readable output."""
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"\n{'='*60}")
        views = int(r['stats']['views'] or 0)
        likes = int(r['stats']['likes'] or 0)
        lines.append(f"{i}. @{r['author']['username']} ({views:,} views, {likes:,} likes)")
        lines.append(f"   {r['url']}")
        lines.append(f"   {r['description'][:200]}")

        if r["hashtags"]:
            lines.append(f"   Tags: {', '.join('#' + h for h in r['hashtags'])}")

        if r["stickers_text"]:
            lines.append(f"   On-screen text: {' | '.join(r['stickers_text'])}")

        if r["location"]:
            loc = r["location"]
            loc_str = loc["name"]
            if loc["address"]:
                loc_str += f" - {loc['address']}"
            if loc["city"]:
                loc_str += f" ({loc['city']})"
            lines.append(f"   Location: {loc_str}")

        if r["transcript"]:
            # Strip WebVTT header and timestamps for readable text
            text_lines = []
            for line in r["transcript"].split("\n"):
                line = line.strip()
                if line and not line.startswith("WEBVTT") and "-->" not in line and not line.isdigit():
                    text_lines.append(line)
            transcript_text = " ".join(text_lines)
            if verbose:
                lines.append(f"   Transcript: {transcript_text}")
            else:
                lines.append(f"   Transcript: {transcript_text[:300]}{'...' if len(transcript_text) > 300 else ''}")
        elif r["caption_available"]:
            lines.append(f"   Transcript: (available but download failed)")
        else:
            lines.append(f"   Transcript: (not available)")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="Search TikTok videos and extract all data")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-n", "--count", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("--no-transcripts", action="store_true", help="Skip downloading transcripts")
    parser.add_argument("--details", action="store_true", help="Also fetch detail endpoint per video (slower, richer data)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    parser.add_argument("--verbose", action="store_true", help="Show full transcripts")
    parser.add_argument("-o", "--output", help="Save JSON results to file")
    args = parser.parse_args()

    results = await search_tiktok(
        query=args.query,
        count=args.count,
        fetch_transcripts=not args.no_transcripts,
        fetch_details=args.details,
    )

    if args.json_output or args.output:
        json_str = json.dumps(results, indent=2, ensure_ascii=False, default=str)
        if args.output:
            with open(args.output, "w") as f:
                f.write(json_str)
            print(f"Saved {len(results)} results to {args.output}")
        if args.json_output:
            print(json_str)
    else:
        print(f"\nFound {len(results)} results for: {args.query}")
        print(format_results(results, verbose=args.verbose))


if __name__ == "__main__":
    asyncio.run(main())
