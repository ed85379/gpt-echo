from pathlib import Path
import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient


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

API_URL = os.getenv("API_URL")
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_SYSTEM_DB = os.getenv("MONGO_SYSTEM_DB")
MONGO_CONVERSATION_COLLECTION = os.getenv("MONGO_CONVERSATION_COLLECTION")
MONGO_FILES_COLLECTION = os.getenv("MONGO_FILES_COLLECTION")
MONGO_MEMORY_COLLECTION = os.getenv("MONGO_MEMORY_COLLECTION")
MONGO_PROJECTS_COLLECTION = os.getenv("MONGO_PROJECTS_COLLECTION")
MONGO_PROFILE_COLLECTION = os.getenv("MONGO_PROFILE_COLLECTION")
MONGO_STATES_COLLECTION = os.getenv("MONGO_STATES_COLLECTION")
MONGO_THREADS_COLLECTION = os.getenv("MONGO_THREADS_COLLECTION")
MONGO_LOGS_COLLECTION = os.getenv("MONGO_LOGS_COLLECTION")

ADMIN_MONGO_URI = os.getenv("ADMIN_MONGO_URI")
ADMIN_MONGO_DB = os.getenv("ADMIN_MONGO_DB")
ADMIN_MONGO_COLLECTION = os.getenv("ADMIN_MONGO_COLLECTION")

QDRANT_CONVERSATION_COLLECTION = os.getenv("QDRANT_CONVERSATION_COLLECTION")
QDRANT_MEMORY_COLLECTION = os.getenv("QDRANT_MEMORY_COLLECTION")
QDRANT_ENTITY_COLLECTION = os.getenv("QDRANT_ENTITY_COLLECTION")
QDRANT_JOURNAL_COLLECTION = os.getenv("QDRANT_JOURNAL_COLLECTION")
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")

GRAPHDB_HOST = os.getenv("GRAPHDB_HOST")
GRAPHDB_PORT = os.getenv("GRAPHDB_PORT")

SENTENCE_TRANSFORMER_ENTITY_MODEL = os.getenv("SENTENCE_TRANSFORMER_ENTITY_MODEL")
SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL")

class MuseConfig:
    def __init__(self, mongo_uri, db_name, live_collection, default_collection):
        self.client = MongoClient(mongo_uri)
        self.live = self.client[db_name][live_collection]
        self.defaults = self.client[db_name][default_collection]

    def get(self, key, default=None):
        # 1. Try live/dynamic setting
        doc = self.live.find_one({"_id": key})
        if doc and "value" in doc:
            return doc["value"]
        # 2. Fallback to default_config collection
        doc = self.defaults.find_one({"_id": key})
        if doc and "value" in doc:
            return doc["value"]
        # 3. Final fallback
        return default

    def set(self, key, value):
        self.live.update_one(
            {"_id": key}, {"$set": {"value": value}}, upsert=True
        )

    def as_dict(self, include_meta=True, pollable_only=False):
        # 1) Load defaults, optionally filtered by pollable
        default_query = {}
        if pollable_only:
            default_query["pollable"] = True

        default_docs = {doc["_id"]: doc for doc in self.defaults.find(default_query)}

        # 2) Load live docs only for the keys we care about
        if default_docs:
            live_query = {"_id": {"$in": list(default_docs.keys())}}
            live_docs = {doc["_id"]: doc for doc in self.live.find(live_query)}
        else:
            live_docs = {}

        # 3) If not pollable_only, we also want any purely-live keys
        if not pollable_only:
            # Grab all live docs, then merge with defaults
            extra_live_docs = {
                doc["_id"]: doc
                for doc in self.live.find({})
                if doc["_id"] not in default_docs
            }
            live_docs.update(extra_live_docs)

        # 4) Union of keys
        all_keys = set(default_docs) | set(live_docs)

        result = {}
        for key in all_keys:
            live_doc = live_docs.get(key)
            default_doc = default_docs.get(key)

            # Value: live > default > None
            if live_doc and "value" in live_doc:
                value = live_doc["value"]
            elif default_doc and "value" in default_doc:
                value = default_doc["value"]
            else:
                value = None

            entry = {"value": value}

            if include_meta:
                # description
                if (live_doc and "description" in live_doc) or (default_doc and "description" in default_doc):
                    entry["description"] = (
                        live_doc.get("description")
                        if live_doc and "description" in live_doc
                        else default_doc.get("description", "")
                    )
                else:
                    entry["description"] = ""

                # category
                if (live_doc and "category" in live_doc) or (default_doc and "category" in default_doc):
                    entry["category"] = (
                        live_doc.get("category")
                        if live_doc and "category" in live_doc
                        else default_doc.get("category", "uncategorized")
                    )
                else:
                    entry["category"] = "uncategorized"


            result[key] = entry

        return result

    def as_grouped(self, include_meta=True):
        """
        Return config as {category: [entries...]} for grouping in the UI.
        Each entry: {"key": ..., "value": ..., "description": ..., "category": ...}
        """
        live_docs = {doc["_id"]: doc for doc in self.live.find({})}
        default_docs = {doc["_id"]: doc for doc in self.defaults.find({})}
        all_keys = set(live_docs) | set(default_docs)

        grouped = {}
        for key in all_keys:
            live_doc = live_docs.get(key)
            default_doc = default_docs.get(key)
            # Value: live > default > None
            if live_doc and "value" in live_doc:
                value = live_doc["value"]
            elif default_doc and "value" in default_doc:
                value = default_doc["value"]
            else:
                value = None

            # Prefer meta fields from live, else fallback to default
            if include_meta:
                if (live_doc and "description" in live_doc) or (default_doc and "description" in default_doc):
                    description = (live_doc.get("description") if live_doc and "description" in live_doc
                                   else default_doc.get("description", ""))
                else:
                    description = ""
                if (live_doc and "category" in live_doc) or (default_doc and "category" in default_doc):
                    category = (live_doc.get("category") if live_doc and "category" in live_doc
                                else default_doc.get("category", "uncategorized"))
                else:
                    category = "uncategorized"
            else:
                description = ""
                category = "uncategorized"

            entry = {
                "key": key,
                "value": value,
                "description": description,
                "category": category
            }
            grouped.setdefault(category, []).append(entry)
        return grouped

muse_config = MuseConfig(
    mongo_uri=MONGO_URI,
    db_name=MONGO_SYSTEM_DB,
    live_collection="muse_config",
    default_collection="default_config"
)

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
LOG_VERBOSITY = get_setting("system_settings.LOG_VERBOSITY", "warn") # error, warn, info, debug
JOURNAL_DIR = PROJECT_ROOT / get_setting("system_settings.JOURNAL_DIR", "journal/")
JOURNAL_CATALOG_PATH = JOURNAL_DIR / get_setting("system_settings.JOURNAL_CATALOG_FILE", "journal_catalog.json")
OPENAI_MODEL = get_setting("system_settings.OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_JOURNALING_MODEL = get_setting("system_settings.OPENAI_JOURNALING_MODEL", "gpt-4.1")
OPENAI_WHISPER_MODEL = get_setting("system_settings.OPENAI_WHISPER_MODEL", "gpt-4.1-nano")
OPENWEATHERMAP_API_URL = get_setting("system_settings.OPENWEATHERMAP_API_URL", "https://api.openweathermap.org/data/2.5/weather")
UNITS = get_setting("system_settings.DEFAULT_UNITS", "imperial")
DISCOVERY_FEEDS = get_setting("system_settings.DISCOVERY_FEEDS", PROFILE_DIR / "discoveryfeeds_sources.json")
MUSE_INTEREST_FEEDS = get_setting("system_settings.MUSE_INTEREST_FEEDS", PROFILE_DIR / "muse_interests_sources.json")
DISCORD_GUILD_NAME = get_setting("system_settings.DISCORD_GUILD_NAME" ,"The Threshold")
DISCORD_CHANNEL_NAME = get_setting("system_settings.DISCORD_CHANNEL_NAME", "echo-chamber")
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

class AdminConfig:
    def __init__(self, mongo_uri, db_name, collection, doc_id="instance_flags"):
        client = MongoClient(mongo_uri)
        self.collection = client[db_name][collection]
        self.doc_id = doc_id

    def get_all(self):
        doc = self.collection.find_one({"_id": self.doc_id}) or {}
        return doc.get("flags", {})

    def get(self, key, default=None):
        flags = self.get_all()
        return flags.get(key, default)

    def set(self, key, value):
        self.collection.update_one(
            {"_id": self.doc_id},
            {"$set": {f"flags.{key}": value}},
            upsert=True,
        )

class UserSettings:
    def __init__(self, mongo_uri, db_name, collection, user_id="primary"):
        client = MongoClient(mongo_uri)
        self.collection = client[db_name][collection]
        self.user_id = user_id

    def get_all(self):
        doc = self.collection.find_one({"_id": self.user_id}) or {}
        return doc

    def get_section(self, section, default=None):
        doc = self.get_all()
        return doc.get(section, default or {})

    def update_section(self, section, data):
        self.collection.update_one(
            {"_id": self.user_id},
            {"$set": {section: data}},
            upsert=True,
        )