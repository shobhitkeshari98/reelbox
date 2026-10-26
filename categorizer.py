"""
Reelbox - AI Categorizer using Gemini
Categorizes reels and extracts key information
"""

import os
import json
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Use reliable models with automatic fallbacks
MODELS = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"]

SYSTEM_PROMPT = """You are a content categorizer for a reel/video bookmark manager called Reelbox.

Given the metadata or URL of a saved reel/video, you must categorize it.
If metadata (title/description) is limited or empty, deduce the best guess category from the platform, author, or URL context. If truly unknown, use "Other" and subcategory "Uncategorized".

Categories to choose from:
- Design (UI/UX, graphic design, web design, typography, branding)
- Tech & AI (programming, AI tools, tech news, software, gadgets)
- Movies & Shows (movie recommendations, reviews, trailers, TV shows, anime)
- Food & Cooking (recipes, restaurant reviews, food hacks, cooking tips)
- Music (songs, playlists, music production, instruments)
- Fitness & Health (workouts, yoga, nutrition, mental health)
- Travel (destinations, travel tips, vlogs, hidden gems)
- Business & Finance (startups, investing, money tips, career advice)
- Education (tutorials, courses, study tips, science, history)
- Fashion & Beauty (outfits, skincare, grooming, style tips)
- Humor & Memes (funny videos, comedy, memes)
- Motivation & Self-help (productivity, mindset, life advice)
- Photography & Videography (camera tips, editing, gear)
- Tools & Apps (app recommendations, productivity tools, browser extensions)
- Other (if nothing fits or unknown)

Respond ONLY with valid JSON in this exact structure:
{
  "headline": "Short 4-8 word punchy bookmark title",
  "category": "Design",
  "subcategory": "Figma Tips",
  "tags": ["figma", "ui", "design"],
  "summary": "Short 1-2 sentence summary of what this reel is about.",
  "key_points": ["Point 1", "Point 2"]
}
"""


async def categorize_reel(metadata: dict) -> dict:
    """
    Use Gemini to categorize a reel and extract key information.
    Tries fallback models if primary model is unavailable.
    """
    user_prompt = (
        f"Categorize this reel/video:\n"
        f"URL: {metadata.get('url', '')}\n"
        f"Platform: {metadata.get('platform', '')}\n"
        f"Title: {metadata.get('title', '')}\n"
        f"Description/Caption: {metadata.get('description', '')}\n"
        f"Author: {metadata.get('author_name', '')}\n"
        f"User Notes: {metadata.get('user_notes', '')}\n"
    )

    last_error = None
    for model_name in MODELS:
        try:
            # Run in worker thread to prevent blocking the async loop
            def call_gemini():
                return client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT + "\n\n" + user_prompt)]),
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=1024,
                        response_mime_type="application/json",
                    ),
                )

            response = await asyncio.to_thread(call_gemini)
            text = response.text.strip()

            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            result = json.loads(text)
            headline = result.get("headline") or result.get("subcategory") or "Saved Bookmark"
            return {
                "title": headline,
                "category": result.get("category", "Other"),
                "subcategory": result.get("subcategory", "General"),
                "tags": result.get("tags", []),
                "summary": result.get("summary", "Saved link"),
                "key_points": result.get("key_points", []),
            }

        except Exception as e:
            last_error = e
            # Try next model
            continue

    print(f"All Gemini models failed: {last_error}")
    # Fallback default so user is never blocked
    platform = metadata.get("platform", "link").capitalize()
    return {
        "category": "Other",
        "subcategory": f"{platform} Reel",
        "tags": [metadata.get("platform", "link")],
        "summary": metadata.get("title") or metadata.get("description") or f"Saved {platform} reel",
        "key_points": [],
    }
