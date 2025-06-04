# <editor-fold desc="🔧 Imports and Configuration">
import json
import time
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
from dateutil.parser import parse as parse_datetime
from zoneinfo import ZoneInfo
from bson import ObjectId
from bson.errors import InvalidId
from sentence_transformers import SentenceTransformer
from croniter import croniter
from app import config
from app.config import muse_config
from app.core import utils
from app.databases.mongo_connector import mongo
from app.services import openai_client
from app.databases import memory_indexer


# </editor-fold>

# --------------------------
# Setup and Configuration
# --------------------------
# <editor-fold desc="🗂 Directory Setup & Constants">
PROJECT_ROOT = config.PROJECT_ROOT
PROFILE_DIR = config.PROFILE_DIR
VALID_ROLES = {"user", "muse", "friend"}
model = SentenceTransformer(config.SENTENCE_TRANSFORMER_MODEL)

# </editor-fold>

# --------------------------
# Chronicle Logging
# --------------------------
# <editor-fold desc="📝 Logging Functions">
def log_message(role, content, source="frontend", metadata=None, flags=None, user_tags=None, timestamp=None):
    """
    Log a message from any source into the Muse system.
    If timestamp is provided (as str or datetime), use/normalize it; otherwise, use now().
    """
    # Normalize timestamp if provided
    if timestamp:
        if isinstance(timestamp, str):
            try:
                timestamp = parse_datetime(timestamp)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                else:
                    timestamp = timestamp.astimezone(timezone.utc)
            except Exception as e:
                print(f"[timestamp parse error]: {e}")
                timestamp = datetime.now(timezone.utc)
        elif not isinstance(timestamp, datetime):
            # Unknown format, fallback
            print(f"[timestamp type error]: Unrecognized timestamp type: {type(timestamp)}")
            timestamp = datetime.now(timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    # Always auto-tag the message
    try:
        auto_tags = openai_client.get_openai_autotags(content)
    except Exception as e:
        auto_tags = []
        print(f"[auto-tag error]: {e}")

    log_entry = {
        "timestamp": timestamp,
        "role": role,
        "source": source,
        "message": content,
        "auto_tags": auto_tags,
        "user_tags": [],
        "flags": flags,
        "metadata": metadata or {},
        "updated_on": timestamp
    }

    try:
        log_entry["message_id"] = memory_indexer.assign_message_id(log_entry)
        mongo.insert_log(muse_config.get("MONGO_CONVERSATION_COLLECTION"), log_entry)
        memory_indexer.build_index(message_id=log_entry["message_id"])
    except Exception as e:
        with open("message_backup.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")


def log_message_test(role, content, source="frontend", metadata=None, flags=None, user_tags=None, timestamp=None):
    """
    Log a message from any source into the Muse system.
    If timestamp is provided (as str or datetime), use/normalize it; otherwise, use now().
    """
    # Normalize timestamp if provided
    if timestamp:
        if isinstance(timestamp, str):
            try:
                timestamp = parse_datetime(timestamp)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                else:
                    timestamp = timestamp.astimezone(timezone.utc)
            except Exception as e:
                print(f"[timestamp parse error]: {e}")
                timestamp = datetime.now(timezone.utc)
        elif not isinstance(timestamp, datetime):
            # Unknown format, fallback
            print(f"[timestamp type error]: Unrecognized timestamp type: {type(timestamp)}")
            timestamp = datetime.now(timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    # Always auto-tag the message
    try:
        auto_tags = openai_client.get_openai_autotags(content)
    except Exception as e:
        auto_tags = []
        print(f"[auto-tag error]: {e}")

    log_entry = {
        "timestamp": timestamp,
        "role": role,
        "source": source,
        "message": content,
        "auto_tags": auto_tags,
        "user_tags": user_tags or [],
        "flags": flags,
        "metadata": metadata or {},
        "updated_on": timestamp
    }

    try:
        log_entry["message_id"] = memory_indexer.assign_message_id(log_entry)
        mongo.insert_log("test_collection", log_entry)
        ## Do not index for tests
        #memory_indexer.build_index(message_id=log_entry["message_id"])
    except Exception as e:
        with open("message_backup.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")

def do_import(collection):
    temp_coll = mongo.db[collection]
    main_coll = mongo.db[muse_config.get("MONGO_CONVERSATION_COLLECTION")]

    imported = 0
    total = temp_coll.count_documents({"imported": {"$ne": True}})
    for doc in temp_coll.find({"imported": {"$ne": True}}):
        log_message(
            role=doc.get("role"),
            content=doc.get("message"),
            source=doc.get("source"),
            timestamp=doc.get("timestamp"),
        )
        temp_coll.update_one({"_id": doc["_id"]}, {"$set": {"imported": True}})
        imported += 1

    mongo.db.import_history.update_one(
        {"collection": collection},
        {"$set": {"processing": False, "status": "imported"}}
    )
    print(f"Imported {imported} of {total} messages for {collection}")

# </editor-fold>

# --------------------------
# Memory Vector Indexing
# --------------------------
# <editor-fold desc="📚 Memory Vector Indexing">
def get_immediate_context(n=10, hours=2):
    now = datetime.utcnow()
    since = now - timedelta(hours=hours)
    query = {
       "timestamp": {"$gte": since}
    }
    # We want the *most recent* messages, so sort descending (ascending=False)
    # This will get up to N most recent within the time window
    logs = mongo.find_logs(
        collection_name="muse_conversations",
        query=query,
        limit=n,
        sort_field="timestamp",
        ascending=False
    )
    # Now reverse so they're in chronological order (oldest first)
    return list(reversed(logs))

def recency_weight(ts, now=None, half_life_hours=36):
    if not ts:
        return 1.0
    if now is None:
        now = datetime.now(timezone.utc).timestamp()
    # Convert ts to timestamp float if needed
    if isinstance(ts, datetime):
        ts = ts.timestamp()
    elif isinstance(ts, str):
        # Try to parse as ISO format
        try:
            ts = datetime.fromisoformat(ts)
            ts = ts.timestamp()
        except Exception:
            # Fallback: try parsing other common formats or just ignore
            return 1.0
    # Now both are float (seconds since epoch)
    age_hours = (now - ts) / 3600
    return 2 ** (-age_hours / half_life_hours)

def tag_weight(payload, tag_boost=1.2, muse_boost=1.15, remembered_boost=2.0):
    score = 1.0
    if payload.get("user_tags"):
        score *= tag_boost
    if payload.get("muse_tags"):
        score *= muse_boost
    if payload.get("remembered"):
        score *= remembered_boost
    return score

def search_indexed_memory(
    query,
    top_k=5,
    bias_author_id=None,
    bias_source=None,
    score_boost=0.1,
    source_boost=0.1,
    penalize_muse=True,
    muse_penalty=0.05,
    recency_half_life=48,         # new
    tag_boost=1.2, muse_boost=1.15, remembered_boost=2.0  # new
):
    """
    Search indexed memory via Qdrant or FAISS.

    Parameters:
    - query (str): Search query.
    - top_k (int): Number of top results to return.
    - bias_author_id (str|None): Optional. Boost results by this author.
    - bias_source (str|None): Optional. Boost results from this source (e.g., 'discord').
    - score_boost (float): Score boost for matching author_id.
    - source_boost (float): Score boost for matching source.
    - penalize_muse (bool): If True, apply a penalty to Muse's own messages.
    - muse_penalty (float): Score penalty for Muse's own responses.

    Returns:
    - List[dict]: Ranked search results.
    """
    query_vector = model.encode([query])[0]


    from qdrant_client import QdrantClient

    QDRANT_HOST = muse_config.get("QDRANT_HOST")
    QDRANT_PORT = int(muse_config.get("QDRANT_PORT"))
    QDRANT_COLLECTION = muse_config.get("QDRANT_COLLECTION")

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    search_result = client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_vector.tolist(),
        limit=top_k
    )

    results = []
    now = time.time()
    for hit in search_result:
        entry = {
            "timestamp": hit.payload.get("timestamp"),
            "message_id": hit.payload.get("message_id"),
            "role": hit.payload.get("role"),
            "source": hit.payload.get("source"),
            "message": hit.payload.get("message"),
            "metadata": hit.payload.get("metadata", {}),
            "score": hit.score,
            "user_tags": hit.payload.get("user_tags"),
            "muse_tags": hit.payload.get("muse_tags"),
            "remembered": hit.payload.get("remembered", False),
        }
        # Old bias stuff...
        if bias_author_id and entry["metadata"].get("author_id") == bias_author_id:
            entry["score"] += score_boost
        if bias_source and entry.get("source") == bias_source:
            entry["score"] += source_boost
        if penalize_muse and entry.get("role") == "muse":
            entry["score"] -= muse_penalty

        # 🟣 New weighting:
        entry["score"] *= recency_weight(entry["timestamp"], now, half_life_hours=recency_half_life)
        entry["score"] *= tag_weight(entry, tag_boost, muse_boost, remembered_boost)
        results.append(entry)

    return sorted(results, key=lambda x: x["score"], reverse=True)


# </editor-fold>

# --------------------------
# MuseCortex Interface
# --------------------------
# <editor-fold desc="🧠 MuseCortex Backends (Mongo + Local)">
try:
    from pymongo import MongoClient
    MONGO_ENABLED = True
except ImportError:
    MONGO_ENABLED = False

class MuseCortexInterface:
    def get_entries_by_type(self, type_name):
        raise NotImplementedError

    def add_entry(self, entry):
        raise NotImplementedError

    def edit_entry(self, entry_id, new_data):
        raise NotImplementedError

    def delete_entry(self, entry_id):
        raise NotImplementedError

    def get_all_entries(self):
        raise NotImplementedError

    def search_by_tag(self, tag):
        raise NotImplementedError

    def search_cortex_for_timely_reminders(self, window_minutes):
        raise NotImplementedError

class MongoCortexClient(MuseCortexInterface):
    def __init__(self):
        uri = muse_config.get("MONGO_URI")
        self.client = MongoClient(uri)
        self.db = self.client["muse_memory"]
        self.collection = self.db["muse_cortex"]

    def get_entries_by_type(self, type_name):
        return list(self.collection.find({"type": type_name}))

    def add_entry(self, entry):
        entry["created_at"] = datetime.now(timezone.utc).isoformat()
        self.collection.insert_one(entry)

    def edit_entry(self, entry_id, new_data):
        # Try as ObjectId first, fall back to plain string if it fails
        query = {"_id": None}
        try:
            query["_id"] = ObjectId(entry_id)
        except (InvalidId, TypeError):
            query["_id"] = entry_id
        res = self.collection.update_one(query, {"$set": new_data})
        return res.modified_count > 0

    def delete_entry(self, entry_id):
        query = {"_id": None}
        try:
            query["_id"] = ObjectId(entry_id)
        except (InvalidId, TypeError):
            query["_id"] = entry_id
        res = self.collection.delete_one(query)
        return res.deleted_count > 0

    def get_all_entries(self):
        return list(self.collection.find())

    def search_by_tag(self, tag):
        return list(self.collection.find({"tags": tag}))

    def search_cortex_for_timely_reminders(self, window_minutes=0.5):
        user_tz = ZoneInfo(muse_config.get("USER_TIMEZONE"))  # e.g., "America/New_York"
        now_local = datetime.now(user_tz)
        lower_bound = now_local - timedelta(minutes=window_minutes)
        upper_bound = now_local + timedelta(minutes=window_minutes)

        reminders = self.get_entries_by_type("reminder")
        triggered = []

        for entry in reminders:
            cron = utils.align_cron_for_croniter(entry.get("cron"))
            skip_until = entry.get("skip_until")
            try:
                # Start base_time slightly before now to catch edge triggers
                base_time = now_local - timedelta(minutes=5)
                # Respect skip_until if provided
                if skip_until:
                    skip_dt = datetime.fromisoformat(skip_until)
                    if skip_dt.tzinfo is None:
                        skip_dt = skip_dt.replace(tzinfo=user_tz)
                    else:
                        skip_dt = skip_dt.astimezone(user_tz)
                    if skip_dt > base_time:
                        base_time = skip_dt
                # Generate next fire time
                itr = croniter(cron, base_time)
                try:
                    next_trigger = itr.get_next(datetime)
                    if next_trigger.tzinfo is None:
                        next_trigger = next_trigger.replace(tzinfo=user_tz)
                except Exception as e:
                    print(f"Error parsing cron for reminder: {e}")
                    continue
                if next_trigger.tzinfo is None:
                    next_trigger = next_trigger.replace(tzinfo=user_tz)

                # Compare to now window
                if lower_bound <= next_trigger <= upper_bound:
                    ends_on = entry.get("ends_on")
                    if ends_on:
                        ends = datetime.fromisoformat(ends_on)
                        if ends.tzinfo is None:
                            ends = ends.replace(tzinfo=user_tz)
                        else:
                            ends = ends.astimezone(user_tz)
                        if next_trigger > ends:
                            continue  # Skip expired reminders
                    triggered.append(entry)

            except Exception as e:
                print(f"❌ Error processing reminder: {e}")
                continue

        print(f"✅ Found {len(triggered)} reminders ready to fire.")
        return triggered


# </editor-fold>

# --------------------------
# Cortex Loader
# --------------------------
# <editor-fold desc="⚙️ Cortex Loader and Global Instance">
def get_cortex():
    try:
        return MongoCortexClient()
    except Exception as e:
        print(f"Mongo unavailable: {e}")


# Global instance
cortex = get_cortex()
# </editor-fold>

