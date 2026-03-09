#!/usr/bin/env python3
"""
fetch_metro_travel.py
--------------------
Fetches YouTube videos, travel blogs, and talks covering major global metro 
cities (guides, street food, transit tips, safety).
Writes METRO_TRAVEL_TALKS.md in the ss repo root.

Retention policy: talks are kept for 1 year from their first-fetch date.
If a YouTube run returns no results the existing list is preserved (not wiped).

Run with the agenticSOC venv which has youtubesearchpython installed:
    /path/to/agenticSOC/venv/bin/python fetch_metro_travel.py
"""

import os
import re
from datetime import datetime, timezone, timedelta

import pytz
from youtubesearchpython import VideosSearch

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ONE_YEAR_AGO = datetime.now(timezone.utc) - timedelta(days=365)

# METRO_TRAVEL_TALKS.md lives in the ss repo root (one level up from scripts/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "METRO_TRAVEL_TALKS.md")

QUERIES = [
    "New York City NYC subway travel vlog guide",
    "Tokyo train etiquette street food travel blog",
    "London Underground travel tips vlog",
    "Mumbai local train street food vlog",
    "Seoul metro street food travel guide",
    "Mexico City CDMX travel vlog safety",
    "Dubai metro luxury travel vlog",
    "Paris travel guide walking tour metro",
    "São Paulo travel vlog guide",
    "Calcutta Kolkata street food walking vlog",
    "Los Angeles LA traffic travel vlog",
    "Chicago L train deep dish travel guide",
    "Shanghai metro street food vlog",
]

# Row regex matching the format written by write_markdown()
ROW_RE = re.compile(
    r"^\|\s*(?P<title>.+?)\s*\|\s*(?P<channel>.+?)\s*\|\s*(?P<duration>.+?)\s*\|"
    r"\s*(?P<views>.+?)\s*\|\s*\[Link\]\((?P<link>https?://[^\)]+)\)\s*\|"
    r"\s*(?P<fetched>\d{4}-\d{2}-\d{2})\s*\|$"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_existing_talks() -> list[dict]:
    """Read METRO_TRAVEL_TALKS.md and return entries whose Fetched date is within 1 year."""
    if not os.path.exists(OUTPUT_FILE):
        return []

    kept: list[dict] = []
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            m = ROW_RE.match(line.rstrip())
            if not m:
                continue
            try:
                fetched_dt = datetime.strptime(m.group("fetched"), "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                fetched_dt = datetime.now(timezone.utc)

            if fetched_dt >= ONE_YEAR_AGO:
                kept.append(
                    {
                        "title": m.group("title"),
                        "link": m.group("link"),
                        "channel": m.group("channel"),
                        "duration": m.group("duration"),
                        "views": m.group("views"),
                        "fetched": m.group("fetched"),
                    }
                )

    print(f"Retained {len(kept)} existing talk(s) (within the last year).")
    return kept


def fetch_new_talks() -> list[dict]:
    """Search YouTube for fresh metro travel and vlog content."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fresh: list[dict] = []
    seen_urls: set[str] = set()

    print("Fetching global metro travel vlogs from YouTube...")
    for query in QUERIES:
        print(f"  Searching: {query}")
        try:
            results = VideosSearch(query, limit=10).result()
            for video in results.get("result", []):
                link = video["link"]
                if link not in seen_urls:
                    seen_urls.add(link)
                    fresh.append(
                        {
                            "title": video["title"],
                            "link": link,
                            "channel": video["channel"]["name"],
                            "duration": video["duration"],
                            "views": video["viewCount"]["short"],
                            "fetched": today,
                        }
                    )
        except Exception as exc:
            print(f"  Error for '{query}': {exc}")

    print(f"Found {len(fresh)} new talk(s) from YouTube this run.")
    return fresh


def merge_talks(existing: list[dict], new: list[dict]) -> list[dict]:
    """Combine new + existing, deduplicate by URL."""
    seen: set[str] = set()
    merged: list[dict] = []
    for talk in new:
        if talk["link"] not in seen:
            seen.add(talk["link"])
            merged.append(talk)
    for talk in existing:
        if talk["link"] not in seen:
            seen.add(talk["link"])
            merged.append(talk)
    return merged


def write_markdown(talks: list[dict]) -> None:
    """Write METRO_TRAVEL_TALKS.md with the merged list."""
    now_str = datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md = "# Global Metro Cities: Travel Blogs & YouTube Talks\n\n"
    md += f"Last Updated: {now_str}\n\n"
    md += (
        "A curated list of YouTube travel blogs, transit guides, street food tours, "
        "and cultural overviews for major global metropolitan cities. Automatically "
        "updated weekly. Talks older than 1 year are automatically pruned.\n\n"
        "> See [GLOBAL_SOCIAL_SKILLS_AND_SLANG.md](./GLOBAL_SOCIAL_SKILLS_AND_SLANG.md) "
        "for the written social skills and dialect cheatsheet.\n\n"
    )

    if not talks:
        md += "No talks found.\n"
    else:
        md += "| Title | Channel | Duration | Views | Watch | Fetched |\n"
        md += "|-------|---------|----------|-------|-------|---------|\n"
        for v in talks:
            title = v["title"].replace("|", "-")
            channel = v["channel"].replace("|", "-")
            md += (
                f"| {title} | {channel} | {v['duration']} | {v['views']} "
                f"| [Link]({v['link']}) | {v['fetched']} |\n"
            )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote {os.path.normpath(OUTPUT_FILE)} — {len(talks)} talk(s) total.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def fetch_talks() -> None:
    existing = load_existing_talks()
    new = fetch_new_talks()

    if not new:
        print("No new talks found — retaining existing list (up to 1 year old).")

    merged = merge_talks(existing, new)
    write_markdown(merged)


if __name__ == "__main__":
    fetch_talks()
