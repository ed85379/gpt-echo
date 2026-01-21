import os
import json
import requests
import feedparser
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import requests
from bs4 import BeautifulSoup
from readability import Document
from app import config
from app.config import muse_config

# Configs
PROJECT_ROOT = config.PROJECT_ROOT
OPENWEATHERMAP_API_KEY = config.OPENWEATHERMAP_API_KEY
PROFILE_DIR = config.PROFILE_DIR

# --- Loaders ---

def load_discoveryfeeds_sources():
    """
    Loads external DiscoveryFeeds (world news, weather, etc).
    """
    sources_path = PROFILE_DIR / "discoveryfeeds_sources.json"
    if not os.path.exists(sources_path):
        return []
    with open(sources_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("feeds", [])


def load_muse_interests_sources():
    """
    Loads Muse's personal feeds.
    """
    sources_path = PROFILE_DIR / "muse_interests_sources.json"
    if not os.path.exists(sources_path):
        return []
    with open(sources_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("feeds", [])


# --- Fetchers ---

def fetch_discoveryfeeds(max_per_feed=5):
    """
    Fetches live entries from DiscoveryFeeds sources.
    """
    sources = load_discoveryfeeds_sources()
    feeds = []

    for source in sources:
        if source.get("type") == "rss":
            try:
                feed = feedparser.parse(source["url"])
                for entry in feed.entries[:max_per_feed]:
                    feeds.append({
                        "source": source["name"],
                        "title": entry.get("title", "No Title"),
                        "summary": clean_summary_text(
                            entry.get("summary") or entry.get("description") or ""
                        ),
                        "link": entry.get("link", "")
                    })
            except Exception as e:
                print(f"⚠️ Error fetching {source['name']}: {e}")
        else:
            print(f"⚠️ Unknown feed type for DiscoveryFeed: {source.get('type')}")

    return feeds


def fetch_muse_interests(max_per_feed=5):
    """
    Fetches live entries from Muse's personal interest feeds.
    """
    sources = load_muse_interests_sources()
    feeds = []

    for source in sources:
        if source.get("type") == "rss":
            try:
                feed = feedparser.parse(source["url"])
                for entry in feed.entries[:max_per_feed]:
                    feeds.append({
                        "source": source["name"],
                        "title": entry.get("title", "No Title"),
                        "summary": clean_summary_text(
                            entry.get("summary") or entry.get("description") or ""
                        ),
                        "link": entry.get("link", "")
                    })
            except Exception as e:
                print(f"⚠️ Error fetching {source['name']}: {e}")
        else:
            print(f"⚠️ Unknown feed type for Muse Interest: {source.get('type')}")

    return feeds


def fetch_combined_feeds(max_per_feed=5):
    """
    Combines entries from discoveryfeeds and Muse's interest feeds.
    """
    discovery = fetch_discoveryfeeds(max_per_feed=max_per_feed)
    interests = fetch_muse_interests(max_per_feed=max_per_feed)

    combined = discovery + interests
    # Optional: dedup by title + source
    seen = set()
    unique = []
    for item in combined:
        key = (item["title"], item["source"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique



def clean_summary_text(html: str, max_tokens: int = 200) -> str:
    """
    Strips HTML, extracts all paragraph content, joins them, and truncates to a clean summary.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Gather text from all <p> tags
    paragraphs = [p.get_text().strip() for p in soup.find_all("p")]
    text = " ".join(paragraphs) if paragraphs else soup.get_text()

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Token-limit by word count
    words = text.split()
    if len(words) > max_tokens:
        text = " ".join(words[:max_tokens]) + "…"

    return text



def fetch_full_article(url: str) -> str:
    """
    Fetches the full readable content of a linked article.
    Attempts to extract main body using readability-lxml.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        doc = Document(response.text)
        html = doc.summary()

        # Strip HTML to plain text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        return text.strip()

    except Exception as e:
        print(f"⚠️ Failed to fetch or parse article: {e}")
        return "[Failed to fetch article text]"


