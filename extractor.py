"""
Reelbox - URL metadata extractor
Fetches metadata from Instagram reels, YouTube shorts, and other URLs
"""

import re
import httpx
import json
from urllib.parse import urlparse


def detect_platform(url: str) -> str:
    """Detect which platform a URL belongs to."""
    domain = urlparse(url).netloc.lower()

    if "instagram.com" in domain or "instagr.am" in domain:
        return "instagram"
    elif "youtube.com" in domain or "youtu.be" in domain:
        return "youtube"
    elif "twitter.com" in domain or "x.com" in domain:
        return "twitter"
    elif "tiktok.com" in domain:
        return "tiktok"
    elif "reddit.com" in domain:
        return "reddit"
    elif "linkedin.com" in domain:
        return "linkedin"
    else:
        return "other"


def extract_url_from_text(text: str) -> tuple[str | None, str]:
    """Extract the first URL and any accompanying text/notes from a message."""
    url_pattern = r'https?://[^\s<>\"\']+' 
    match = re.search(url_pattern, text)
    if match:
        url = match.group(0).rstrip('.,;:!?)')
        # Remove the URL from the message to get user notes
        notes = (text[:match.start()] + " " + text[match.end():]).strip()
        return url, notes
    return None, text.strip()


async def fetch_oembed_data(url: str, platform: str) -> dict:
    """Fetch oEmbed data for supported platforms."""
    oembed_endpoints = {
        "instagram": f"https://api.instagram.com/oembed?url={url}&omitscript=true",
        "youtube": f"https://www.youtube.com/oembed?url={url}&format=json",
        "tiktok": f"https://www.tiktok.com/oembed?url={url}",
        "twitter": f"https://publish.twitter.com/oembed?url={url}",
    }

    endpoint = oembed_endpoints.get(platform)
    if not endpoint:
        return {}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(endpoint, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"oEmbed fetch failed for {platform}: {e}")

    return {}


async def fetch_opengraph_data(url: str) -> dict:
    """Fetch Open Graph metadata by scraping the page."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            html = resp.text

            og_data = {}
            # Extract og: meta tags
            og_pattern = r'<meta\s+(?:property|name)="og:(\w+)"\s+content="([^"]*)"'
            for match in re.finditer(og_pattern, html, re.IGNORECASE):
                og_data[match.group(1)] = match.group(2)

            # Also try reverse attribute order
            og_pattern2 = r'<meta\s+content="([^"]*)"\s+(?:property|name)="og:(\w+)"'
            for match in re.finditer(og_pattern2, html, re.IGNORECASE):
                og_data[match.group(2)] = match.group(1)

            # Extract page title as fallback
            title_match = re.search(r'<title>([^<]*)</title>', html, re.IGNORECASE)
            if title_match and "title" not in og_data:
                og_data["title"] = title_match.group(1).strip()

            # Extract meta description as fallback
            desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html, re.IGNORECASE)
            if desc_match and "description" not in og_data:
                og_data["description"] = desc_match.group(1).strip()

            return og_data
    except Exception as e:
        print(f"OpenGraph fetch failed: {e}")
        return {}


async def extract_metadata(url: str) -> dict:
    """
    Extract all available metadata from a URL.
    Returns a normalized dict with title, description, thumbnail, author, etc.
    """
    platform = detect_platform(url)

    # Try oEmbed first (structured data)
    oembed = await fetch_oembed_data(url, platform)

    # Also try OpenGraph as supplement
    og = await fetch_opengraph_data(url)

    # Build normalized metadata
    thumb = (oembed.get("thumbnail_url", "") or og.get("image", "")).replace("&amp;", "&")
    metadata = {
        "url": url,
        "platform": platform,
        "title": oembed.get("title", "") or og.get("title", ""),
        "description": og.get("description", ""),
        "thumbnail_url": thumb,
        "author_name": oembed.get("author_name", "") or og.get("site_name", ""),
        "author_url": oembed.get("author_url", ""),
        "raw_metadata": {
            "oembed": oembed,
            "opengraph": og,
        }
    }

    # For Instagram, extract caption from oEmbed HTML
    if platform == "instagram" and oembed.get("html"):
        caption_match = re.search(r'<p[^>]*>(.*?)</p>', oembed.get("html", ""), re.DOTALL)
        if caption_match:
            caption = re.sub(r'<[^>]+>', '', caption_match.group(1)).strip()
            if caption:
                metadata["description"] = caption

    return metadata
