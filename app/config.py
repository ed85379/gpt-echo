from pathlib import Path
import os
import json
from dotenv import load_dotenv

# Determine project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load static settings
CONFIG_PATH = PROJECT_ROOT / "muse_config.json"

try:
    with open(CONFIG_PATH, "r") as f:
        _settings = json.load(f)
except Exception as e:
    print(f"Error loading muse_config.json: {e}")
    _settings = {}

# Load environment variables
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Secrets from .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PRIMARY_USER_DISCORD_ID = os.getenv("PRIMARY_USER_DISCORD_ID")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

## Fallback for any settings not listed below
def get_setting(key, default=None):
    """
    Supports nested keys like "user_settings.USER_NAME".
    """
    keys = key.split(".")
    value = _settings
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value

## Shortcuts to established config options
# user settngs
USER_NAME = get_setting("user_settings.USER_NAME", "User")
USER_TIMEZONE = get_setting("user_settings.USER_TIMEZONE", "UTC")
USER_ZIPCODE = get_setting("user_settings.USER_ZIPCODE", "67449")
USER_COUNTRYCODE = get_setting("user_settings.USER_COUNTRYCODE", "US")
QUIET_HOURS_START = get_setting("user_settings.QUIET_HOURS_START", 22)
QUIET_HOURS_END = get_setting("user_settings.QUIET_HOURS_END", 10)
# system settings
MUSE_NAME = get_setting("system_settings.MUSE_NAME", "Muse")
PROFILE_DIR = PROJECT_ROOT / get_setting("system_settings.PROFILE_DIR", "profiles/")
SYSTEM_LOGS_DIR = PROJECT_ROOT / get_setting("system_settings.SYSTEM_LOGS_DIR", "logs/system/")
LOG_VERBOSITY = get_setting("system_settings.LOG_VERBOSITY", "normal") # minimal, normal, debug
JOURNAL_DIR = PROJECT_ROOT / get_setting("system_settings.JOURNAL_DIR", "journal/")
JOURNAL_CATALOG_PATH = JOURNAL_DIR / get_setting("system_settings.JOURNAL_CATALOG_FILE", "journal_catalog.json")
OPENAI_MODEL = get_setting("system_settings.OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_JOURNALING_MODEL = get_setting("system_settings.OPENAI_JOURNALING_MODEL", "gpt-4.1")
OPENAI_WHISPER_MODEL = get_setting("system_settings.OPENAI_WHISPER_MODEL", "gpt-4.1-nano")
SENTENCE_TRANSFORMER_MODEL = get_setting("system_settings.SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
OPENWEATHERMAP_API_URL = get_setting("system_settings.OPENWEATHERMAP_API_URL", "https://api.openweathermap.org/data/2.5/weather")
UNITS = get_setting("system_settings.DEFAULT_UNITS", "imperial")
DISCOVERY_FEEDS = get_setting("system_settings.DISCOVERY_FEEDS", PROFILE_DIR / "discoveryfeeds_sources.json")
MUSE_INTEREST_FEEDS = get_setting("system_settings.MUSE_INTEREST_FEEDS", PROFILE_DIR / "muse_interests_sources.json")
DISCORD_GUILD_NAME = get_setting("system_settings.DISCORD_GUILD_NAME" ,"The Threshold")
DISCORD_CHANNEL_NAME = get_setting("system_settings.DISCORD_CHANNEL_NAME", "echo-chamber")
THRESHOLD_API_URL = get_setting("system_settings.THRESHOLD_API_URL", "http://localhost:5000")
QDRANT_HOST = get_setting("system_settings.QDRANT_HOST", "localhost")
QDRANT_PORT = get_setting("system_settings.QDRANT_PORT", 6333)
QDRANT_COLLECTION = get_setting("system_settings.QDRANT_COLLECTION", "muse_memory")
QDRANT_JOURNAL_COLLECTION = get_setting("system_settings.QDRANT_JOURNAL_COLLECTION", "muse_journal")
MONGO_DBNAME = get_setting("system_settings.MONGO_DBNAME", "muse_memory")
MONGO_CONVERSATION_COLLECTION = get_setting("system_settings.MONGO_CONVERSATION_COLLECTION", "muse_conversation_logs")
GRAPHDB_HOST = get_setting("system_settings.GRAPHDB_HOST", "localhost")
GRAPHDB_PORT = get_setting("system_settings.GRAPHDB_PORT", 7687)
MONGO_URI = get_setting("system_settings.MONGO_URL", "mongodb://localhost:27017/")
ENABLE_PRIVATE_JOURNAL = get_setting("system_settings.ENABLE_PRIVATE_JOURNAL", "False")
# voice settings
VOICE_SYSTEM = get_setting("voice_settings.VOICE_SYSTEM", "coqui")
TTS_VOICE_ID = get_setting("voice_settings.TTS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
TTS_SPEED = get_setting("voice_settings.TTS_SPEED", "1.0")
VOICE_OUTPUT_DIR = PROJECT_ROOT / get_setting("voice_settings.VOICE_OUTPUT_DIR", "voice/")
AUDIO_OUTPUT_PATH = get_setting("voice_settings.AUDIO_OUTPUT_PATH", VOICE_OUTPUT_DIR / "response.mp3")
INPUT_DEVICE = get_setting("voice_settings.INPUT_DEVICE", "default")
OUTPUT_DEVICE = get_setting("voice_settings.OUTPUT_DEVICE", "default")
SPEAK_OUT_LOUD = get_setting("voice_settings.SPEAK_OUT_LOUD", "False")
# behavior_settings
HEARTBEAT_INTERVAL_SECONDS = get_setting("behavior_settings.HEARTBEAT_INTERVAL_SECONDS", 600)
SPEAK_ENDPOINTS = get_setting("behavior_settings.SPEAK_ENDPOINTS", ["discord"])
REFLECT_TARGETS = get_setting("behavior_settings.REFLECT_TARGETS", [])
MUSE_PRIMARY_FLAVOR = get_setting("behavior_settings.MUSE_PRIMARY_FLAVOR", "poetic-reflective")
MAX_ARTICLE_WORDS_BEFORE_SUMMARIZE = get_setting("behavior_settings.MAX_ARTICLE_WORDS_BEFORE_SUMMARIZE", 500)

