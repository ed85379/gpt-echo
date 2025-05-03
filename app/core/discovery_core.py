import os
import json
import requests
import feedparser
from datetime import datetime
from zoneinfo import ZoneInfo
from app import config

# Configs
PROJECT_ROOT = config.PROJECT_ROOT
OPENWEATHERMAP_API_KEY = config.OPENWEATHERMAP_API_KEY
USER_TIMEZONE = config.get_setting("user_settings.USER_TIMEZONE", "UTC")
PROFILE_DIR = PROJECT_ROOT / config.get_setting("system_settings.PROFILE_DIR", "profiles/")
zip_code = config.get_setting("user_settings.USER_ZIPCODE", "02149")
country_code = config.get_setting("user_settings.USER_COUNTRYCODE", "US")

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


def load_echos_interests_sources():
    """
    Loads Echo's personal feeds.
    """
    sources_path = PROFILE_DIR / "echos_interests_sources.json"
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
                        "summary": entry.get("summary", ""),
                        "link": entry.get("link", "")
                    })
            except Exception as e:
                print(f"⚠️ Error fetching {source['name']}: {e}")
        else:
            print(f"⚠️ Unknown feed type for DiscoveryFeed: {source.get('type')}")

    return feeds


def fetch_echos_interests(max_per_feed=5):
    """
    Fetches live entries from Echo's personal interest feeds.
    """
    sources = load_echos_interests_sources()
    feeds = []

    for source in sources:
        if source.get("type") == "rss":
            try:
                feed = feedparser.parse(source["url"])
                for entry in feed.entries[:max_per_feed]:
                    feeds.append({
                        "source": source["name"],
                        "title": entry.get("title", "No Title"),
                        "summary": entry.get("summary", ""),
                        "link": entry.get("link", "")
                    })
            except Exception as e:
                print(f"⚠️ Error fetching {source['name']}: {e}")
        else:
            print(f"⚠️ Unknown feed type for Echo Interest: {source.get('type')}")

    return feeds


# --- Local Environmental Awareness ---
def get_local_weather(zip_code=zip_code, country_code=country_code, units="imperial"):
    """
    Fetches current weather conditions by ZIP code.
    """
    if not OPENWEATHERMAP_API_KEY:
        return "Weather data unavailable (missing API key)."

    url = f"https://api.openweathermap.org/data/2.5/weather?zip={zip_code},{country_code}&appid={OPENWEATHERMAP_API_KEY}&units={units}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            description = data["weather"][0]["description"].capitalize()
            temp = data["main"]["temp"]
            return f"{description}, {temp}°F"
        else:
            print(f"⚠️ Weather fetch error: {response.status_code} - {response.text}")
            return "Weather data unavailable."
    except Exception as e:
        print(f"⚠️ Weather fetch exception: {e}")
        return "Weather data unavailable."



def get_local_time():
    """
    Returns the current local time formatted cleanly.
    """
    now = datetime.now(ZoneInfo(USER_TIMEZONE))
    return now.strftime("%I:%M %p on %A")
