#!/usr/bin/env python3
"""Daily wallpaper picker.

Aggregates image candidates from:
  - AstroBin Image of the Day (last ~10 days, via RSS)
  - Nikon Small World photomicrography competition (most recent year, via gallery scrape)

Picks the image whose aspect ratio is closest to the primary display, downloads
it, and sets it as the macOS wallpaper. Run daily via launchd.
"""
from __future__ import annotations

import datetime as dt
import os
import random
import re
import struct
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
DEST = Path.home() / "Pictures" / "DailyWallpaper"
DEST.mkdir(parents=True, exist_ok=True)
LOG = DEST / "wallpaper.log"


def log(msg: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line)
    with LOG.open("a") as f:
        f.write(line + "\n")


def fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def jpeg_dims(head: bytes) -> tuple[int, int] | None:
    if head[:3] != b"\xff\xd8\xff":
        return None
    i = 2
    try:
        while i < len(head):
            while head[i] == 0xFF:
                i += 1
            marker = head[i]
            i += 1
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h = struct.unpack(">H", head[i + 3 : i + 5])[0]
                w = struct.unpack(">H", head[i + 5 : i + 7])[0]
                return w, h
            seg = struct.unpack(">H", head[i : i + 2])[0]
            i += seg
    except Exception:
        return None
    return None


def png_dims(head: bytes) -> tuple[int, int] | None:
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    try:
        w = struct.unpack(">I", head[16:20])[0]
        h = struct.unpack(">I", head[20:24])[0]
        return w, h
    except Exception:
        return None


def probe_dims(url: str) -> tuple[int, int] | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-16384"})
        with urllib.request.urlopen(req, timeout=10) as r:
            head = r.read(16384)
        return jpeg_dims(head) or png_dims(head)
    except Exception:
        return None


# ---------- Sources ----------

def source_astrobin() -> list[dict]:
    log("fetching AstroBin IOTD feed")
    try:
        data = fetch("https://www.astrobin.com/iotd/rss/iotd")
    except Exception as e:
        log(f"astrobin feed failed: {e}")
        return []
    root = ET.fromstring(data)
    out = []
    for item in root.findall(".//item"):
        enc = item.find("enclosure")
        if enc is None:
            continue
        url = enc.attrib.get("url", "")
        m = re.search(r"_(\d+)x(\d+)_", url)
        w, h = (int(m.group(1)), int(m.group(2))) if m else (None, None)
        if w and (not h):
            dims = probe_dims(url)
            if not dims:
                continue
            w, h = dims
        if not (w and h):
            continue
        out.append({
            "source": "astrobin",
            "title": (item.findtext("title") or "").strip(),
            "author": (item.findtext("{http://purl.org/dc/elements/1.1/}creator") or "").strip(),
            "url": url,
            "w": w,
            "h": h,
        })
    log(f"astrobin: {len(out)} candidates")
    return out


def source_apod(limit: int = 7) -> list[dict]:
    log("fetching NASA APOD feed")
    try:
        data = fetch("https://apod.nasa.gov/apod.rss")
    except Exception as e:
        log(f"apod feed failed: {e}")
        return []
    root = ET.fromstring(data)
    pages = [(item.findtext("link") or "").strip() for item in root.findall(".//item")[:limit]]
    pages = [p for p in pages if p]

    def resolve(page: str) -> dict | None:
        try:
            html = fetch(page).decode("utf-8", errors="replace")
        except Exception:
            return None
        m = re.search(r'<a\s+href="(image/\d{4}/[^"]+\.(?:jpg|jpeg|png))"', html, re.I)
        if not m:
            return None
        img_url = "https://apod.nasa.gov/apod/" + m.group(1)
        dims = probe_dims(img_url)
        if not dims:
            return None
        title_match = re.search(r"<title>\s*APOD:\s*[^-]+-\s*([^<]+)</title>", html, re.I)
        title = (title_match.group(1).strip() if title_match else Path(m.group(1)).stem).strip()
        return {"source": "apod", "title": title, "author": "", "url": img_url, "w": dims[0], "h": dims[1]}

    with ThreadPoolExecutor(max_workers=8) as pool:
        out = [r for r in pool.map(resolve, pages) if r]
    log(f"apod: {len(out)} candidates")
    return out


def source_nikon(sample_size: int = 15) -> list[dict]:
    """Pick a random year from the past decade of Small World competitions,
    scrape its gallery, then probe a random sample of thumbnails in parallel."""
    current = dt.date.today().year
    years = list(range(current - 9, current + 1))
    random.shuffle(years)
    html = None
    for y in years:
        gallery_url = f"https://www.nikonsmallworld.com/galleries/{y}-photomicrography-competition"
        try:
            body = fetch(gallery_url).decode("utf-8", errors="replace")
            if "thumbnails/" in body:
                html = body
                log(f"nikon: using gallery {y}")
                break
        except Exception:
            continue
    if not html:
        log("nikon: no gallery fetched")
        return []

    pattern = re.compile(
        r"https://downloads\.microscope\.healthcare\.nikon\.com/smallworld/thumbnails/(\d{4})/([^\"'<> ]+\.(?:jpg|jpeg|png))",
        re.I,
    )
    seen: set[str] = set()
    entries: list[tuple[str, str]] = []
    for m in pattern.finditer(html):
        thumb_year, fname = m.group(1), m.group(2)
        if fname in seen:
            continue
        seen.add(fname)
        entries.append((thumb_year, fname))
    random.shuffle(entries)
    entries = entries[:sample_size]

    def resolve(e: tuple[str, str]) -> dict | None:
        thumb_year, fname = e
        for url in (
            f"https://www.nikonsmallworld.com/images/photos/{thumb_year}/{fname}",
            f"https://www.nikonsmallworld.com/images/photos/{thumb_year}/_photo1600/{fname}",
        ):
            dims = probe_dims(url)
            if dims:
                return {
                    "source": "nikon",
                    "title": fname.rsplit(".", 1)[0].replace("_", " "),
                    "author": "",
                    "url": url,
                    "w": dims[0],
                    "h": dims[1],
                }
        return None

    with ThreadPoolExecutor(max_workers=10) as pool:
        out = [r for r in pool.map(resolve, entries) if r]
    log(f"nikon: {len(out)} candidates (sampled from {len(seen)})")
    return out


# ---------- Picker ----------

def display_ratio() -> float:
    try:
        out = subprocess.check_output(["system_profiler", "SPDisplaysDataType"], text=True)
        m = re.search(r"Resolution:\s+(\d+)\s*x\s*(\d+)", out)
        if m:
            return int(m.group(1)) / int(m.group(2))
    except Exception:
        pass
    return 16 / 10


def pick_best(candidates: list[dict], target: float) -> dict | None:
    if not candidates:
        return None
    return min(candidates, key=lambda c: abs(c["w"] / c["h"] - target))


def download(cand: dict) -> Path:
    stem = Path(urlparse(cand["url"]).path).name
    today = dt.date.today().isoformat()
    out = DEST / f"{today}_{cand['source']}_{stem}"
    if not out.exists() or out.stat().st_size == 0:
        data = fetch(cand["url"], timeout=60)
        out.write_bytes(data)
    return out


def set_wallpaper(path: Path) -> None:
    """Prefer desktoppr (uses NSWorkspace, respects 'Show on all Spaces').
    Fall back to AppleScript if desktoppr isn't installed."""
    for cmd in (["/usr/local/bin/desktoppr", "all", str(path)],
                ["/opt/homebrew/bin/desktoppr", "all", str(path)]):
        if Path(cmd[0]).exists():
            subprocess.run(cmd, check=True)
            return
    script = f'tell application "System Events" to tell every desktop to set picture to "{path}"'
    subprocess.run(["osascript", "-e", script], check=True)


def cleanup(keep: Path) -> None:
    """Delete previously downloaded wallpapers, keeping only the current one."""
    for f in DEST.iterdir():
        if f == keep or f == LOG or f.is_dir():
            continue
        if f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            try:
                f.unlink()
                log(f"cleaned: {f.name}")
            except Exception as e:
                log(f"cleanup failed {f.name}: {e}")


def main() -> int:
    log("=== start ===")
    ratio = display_ratio()
    log(f"display ratio: {ratio:.4f}")

    sources = {"astrobin": source_astrobin, "apod": source_apod, "nikon": source_nikon}
    order = list(sources.keys())
    random.shuffle(order)
    chosen = None
    for name in order:
        log(f"rolled source: {name}")
        candidates = sources[name]()
        chosen = pick_best(candidates, ratio)
        if chosen:
            break
        log(f"{name} empty, falling back")

    if not chosen:
        log("no candidates available from any source")
        return 1
    log(
        f"picked [{chosen['source']}] {chosen['title']} "
        f"({chosen['w']}x{chosen['h']}, ratio={chosen['w']/chosen['h']:.3f}) -> {chosen['url']}"
    )
    path = download(chosen)
    set_wallpaper(path)
    log(f"wallpaper set: {path}")
    cleanup(keep=path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
