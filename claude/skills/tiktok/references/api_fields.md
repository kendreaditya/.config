# TikTok API Field Reference

## Endpoints

### Search Videos
- **URL**: `https://www.tiktok.com/api/search/item/full/`
- **Method**: GET (via Playwright browser session)
- **Params**: `keyword`, `count` (max 20), `cursor`, `source=search_video`
- **Returns**: `item_list[]`, `has_more`, `cursor`
- **Notes**: Most reliable endpoint. Returns captions/subtitles when available. No auth needed but requires browser session (Playwright).

### Video Detail
- **URL**: `https://www.tiktok.com/api/item/detail/`
- **Params**: `itemId`
- **Returns**: `itemInfo.itemStruct` (same shape as search items but sometimes richer)
- **Notes**: More aggressively bot-detected. Use `headless=False` with chromium. May return richer `subtitleInfos` than search.

## Data Sources Per Video

### 1. Description (`desc`)
Always present. Creator-typed caption text including hashtags.

### 2. Stickers / On-Screen Text (`stickersOnItem[]`)
Array of sticker objects. `stickerType: 4` = text stickers.
```json
{"stickerType": 4, "stickerText": ["Line 1", "Line 2"]}
```

### 3. Location / POI (`poi`)
Tagged location. Not all videos have this.
```json
{
  "name": "Henry Cowell Redwoods State Park",
  "address": "101 N Big Trees Park Rd, Felton, CA 95018",
  "city": "Scotts Valley",
  "category": "Outdoors and Traveling",
  "ttTypeNameTiny": "Nature Park"
}
```

### 4. Transcripts / Captions
Available when `video.claInfo.enableAutoCaption == true`.

Two equivalent sources:
- `video.claInfo.captionInfos[]` — has `urlList[]` with CDN and aweme URLs, `captionFormat: "webvtt"`, `language`, `isAutoGen`
- `video.subtitleInfos[]` — has `Url`, `Format: "webvtt"`, `Source: "ASR"`, `UrlExpire`

Caption URLs are signed and expire (~24h). Download format is WebVTT with timestamps.

**CDN URLs** (`tiktokcdn` domain) work with just a Referer header.
**Aweme URLs** (`tiktok.com/aweme/v1/play/`) also work but less reliably.

~30% of videos have captions enabled. Videos without them return `enableAutoCaption: false` and `noCaptionReason: 2`.

### 5. Other Fields
- `stats` / `statsV2`: playCount, diggCount, commentCount, shareCount, collectCount
- `author`: uniqueId, nickname, verified, followerCount
- `music`: title, authorName, original (bool)
- `challenges[]`: hashtag objects with id, title
- `createTime`: unix timestamp
- `video.duration`: seconds
- `textLanguage`: detected language code
- `contents[]`: description segments with hashtag metadata
