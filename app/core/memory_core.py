# <editor-fold desc="🔧 Imports and Configuration">
import json
import time
import asyncio
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
from dateutil.parser import parse as parse_datetime
from zoneinfo import ZoneInfo
from bson import ObjectId
from bson.errors import InvalidId
from sentence_transformers import SentenceTransformer
from croniter import croniter
from app import config
#from app.api.api_main import QDRANT_COLLECTION
from app.config import muse_config
from app.core.utils import write_system_log, align_cron_for_croniter
from app.core import utils
from app.databases.mongo_connector import mongo
from app.services import openai_client
from app.databases import memory_indexer
from app.api.queues import index_memory_queue
from app.databases.qdrant_connector import delete_point, query as qdrant_query

# </editor-fold>

# --------------------------
# Setup and Configuration
# --------------------------
# <editor-fold desc="🗂 Directory Setup & Constants">
PROJECT_ROOT = config.PROJECT_ROOT
PROFILE_DIR = config.PROFILE_DIR
VALID_ROLES = {"user", "muse", "friend"}
model = SentenceTransformer(muse_config.get("SENTENCE_TRANSFORMER_MODEL"))


# </editor-fold>

# --------------------------
# Chronicle Logging
# --------------------------
# <editor-fold desc="📝 Logging Functions">
async def log_message(role, message, source="frontend", metadata=None, flags=None, user_tags=None, timestamp=None, project_id=None, project_ids=None):
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
        auto_tags = openai_client.get_openai_autotags(message)
    except Exception as e:
        auto_tags = []
        print(f"[auto-tag error]: {e}")

    log_entry = {
        "timestamp": timestamp,
        "role": role,
        "source": source,
        "message": message,
        "auto_tags": auto_tags,
        "user_tags": [],
        "flags": flags,
        "metadata": metadata or {},
        "updated_on": timestamp
    }
    # Only add if provided (and not None)
    if project_id is not None:
        log_entry["project_id"] = ObjectId(project_id)
    if project_ids is not None:
        log_entry["project_ids"] = project_ids

    try:
        log_entry["message_id"] = memory_indexer.assign_message_id(log_entry)
        mongo.insert_log(muse_config.get("MONGO_CONVERSATION_COLLECTION"), log_entry)
        await memory_indexer.build_index(message_id=log_entry["message_id"])
    except Exception as e:
        write_system_log(
            level="error",
            module="core",
            component="memory_core",
            function="log_message",
            action="log_failed",
            error=str(e),
            message=str(json.dumps(log_entry))
        )
        with open("message_backup.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")
    return {"message_id": log_entry["message_id"]}


async def do_import(collection):
    temp_coll = mongo.db[collection]
    main_coll = mongo.db[muse_config.get("MONGO_CONVERSATION_COLLECTION")]

    imported = 0
    total = temp_coll.count_documents({"imported": {"$ne": True}})
    for doc in temp_coll.find({"imported": {"$ne": True}}):
        await log_message(
            role=doc.get("role"),
            message=doc.get("message"),
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
def get_hidden_project_ids():
    query = {"hidden": True}
    projection = {"_id": 1}
    hidden_projects = mongo.find_documents(
        collection_name="muse_projects",
        query=query,
        projection=projection
    )
    return set(p["_id"] for p in hidden_projects)


def get_immediate_context(n=10, hours=2):
    now = datetime.utcnow()
    since = now - timedelta(hours=hours)
    hidden_project_ids = get_hidden_project_ids()

    query = {
        "timestamp": {"$gte": since},
        "source": {"$ne": "file"},
        "is_private": {"$ne": True},       # Exclude private messages
        "is_deleted": {"$ne": True}        # Exclude deleted
    }
    if hidden_project_ids:
        query["$or"] = [
            {"project_id": {"$nin": list(hidden_project_ids)}},  # Single-linked
            {"project_id": {"$exists": False}},  # Unattached
            {"project_ids": {"$exists": True, "$nin": list(hidden_project_ids)}}  # Multi-linked: at least one visible
        ]
        # This way, messages with *no* project_id are always included, unless otherwise filtered

    logs = mongo.find_logs(
        collection_name="muse_conversations",
        query=query,
        limit=n,
        sort_field="timestamp",
        ascending=False
    )
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

def tag_weight(payload, tag_boost=1.2, muse_boost=1.15, remembered_boost=2.0, project_boost=1.25):
    score = 1.0
    if payload.get("user_tags"):
        score *= tag_boost
    if payload.get("muse_tags"):
        score *= muse_boost
    if payload.get("remembered"):
        score *= remembered_boost
    if payload.get("project_id"):  # Any non-empty project_id
        score *= project_boost
    return score

def search_indexed_memory(
    query,
    projects_in_focus=None,     # List[str], e.g. ["proj_abc123"]
    blend_ratio=1.0,            # float: 1.0 = hard project focus, 0.1–0.99 = blended
    top_k=10,
    collection_name="muse_memory",
    bias_author_id=None,
    bias_source=None,
    score_boost=0.1,
    source_boost=0.1,
    penalize_muse=False,
    muse_penalty=0.05,
    recency_half_life=48,
    tag_boost=1.2, muse_boost=1.15, remembered_boost=2.0, project_boost=1.25, non_project_penalty=0.2
):
    """
    Search indexed memory via Qdrant, with Project Focus support.
    """
    if projects_in_focus is None:
        projects_in_focus = []
    query_vector = model.encode([query])[0]
    overfetch_k = top_k * 5

    from qdrant_client import QdrantClient
    QDRANT_HOST = muse_config.get("QDRANT_HOST")
    QDRANT_PORT = int(muse_config.get("QDRANT_PORT"))
    QDRANT_COLLECTION = collection_name

    hidden_project_ids = [str(oid) for oid in get_hidden_project_ids()]
    query_filter = {
        "must_not": [
            {"key": "is_private", "match": {"value": True}},
            {"key": "is_deleted", "match": {"value": True}},
        ]
    }
    if hidden_project_ids:
        query_filter["must_not"].append(
            {"key": "project_id", "match": {"any": hidden_project_ids}}
        )

    # Project focus: hard filter for 100%
    if projects_in_focus and blend_ratio == 1.0:
        query_filter["must"] = [
            {"key": "project_id", "match": {"any": projects_in_focus}}
        ]
        # Note: If you want to also include messages with project_ids array, you'll need to expand filter logic or post-process

    #client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    #search_result = client.search(
    #    collection_name=QDRANT_COLLECTION,
    #    query_vector=query_vector.tolist(),
    #    limit=overfetch_k,
    #    query_filter=query_filter
    #)
    search_result = qdrant_query(QDRANT_COLLECTION, query, overfetch_k, query_filter)

    print("\n[Raw Search Results]")
    for i, hit in enumerate(search_result[:50]):
        pid = hit.payload.get("project_id")
        pids = hit.payload.get("project_ids")
        print(f"  Result[{i}] id={hit.payload.get('message_id')[:6]}, proj_id={pid}, proj_ids={pids}")

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
            "project_id": hit.payload.get("project_id"),
            "project_ids": hit.payload.get("project_ids")
        }
        # Biases
        if bias_author_id and entry["metadata"].get("author_id") == bias_author_id:
            entry["score"] += score_boost
        if bias_source and entry.get("source") == bias_source:
            entry["score"] += source_boost
        if penalize_muse and entry.get("role") == "muse":
            entry["score"] -= muse_penalty

        # Recency & tag weighting
        entry["score"] *= recency_weight(entry["timestamp"], now, half_life_hours=recency_half_life)
        entry["score"] *= tag_weight(entry, tag_boost, muse_boost, remembered_boost, project_boost)
        results.append(entry)

    # Filter out entries with only hidden project_ids (for files, etc.)
    filtered_results = []
    for entry in results:
        pids = entry.get("project_ids")
        if pids is not None:
            if not pids:
                filtered_results.append(entry)
            elif all(pid in hidden_project_ids for pid in pids):
                continue
            else:
                filtered_results.append(entry)
        else:
            filtered_results.append(entry)

    # Project focus blending: only if 10-99% (not hard filter)
    if projects_in_focus and 0.0 < blend_ratio < 1.0:
        # Optional: print blend context
        print(f"\n[Project Focus Blend] projects_in_focus={projects_in_focus}, blend_ratio={blend_ratio}")
        for i, entry in enumerate(filtered_results):
            project_ids = entry.get("project_ids") or []
            in_focus = (
                    (entry.get("project_id") in projects_in_focus)
                    or any(pid in projects_in_focus for pid in project_ids)
            )
            pre_score = entry["score"]
            if in_focus:
                entry["score"] *= 1 + (blend_ratio * project_boost)
            else:
                entry["score"] *= 1 - (blend_ratio * non_project_penalty)
            post_score = entry["score"]

            # Print a compact summary for first few entries
            if i < 5:  # Avoid log spam
                print(
                    f"  Entry[{i}] id={entry.get('message_id')[:6]}..., "
                    f"in_focus={in_focus}, "
                    f"proj_id={entry.get('project_id')}, "
                    f"proj_ids={project_ids}, "
                    f"pre={pre_score:.3f}, post={post_score:.3f}"
                )
        print(f"[Project Focus Blend] Sampled {min(len(filtered_results), 5)} of {len(filtered_results)} entries.")

    # At 100% focus, optionally post-filter any stragglers (such as project_ids files) for complete purity:
    if projects_in_focus and blend_ratio == 1.0:
        before = len(filtered_results)
        filtered_results = [
            entry for entry in filtered_results
            if (
                    (entry.get("project_id") in projects_in_focus)
                    or any(pid in projects_in_focus for pid in entry.get("project_ids", []))
            )
        ]
        after = len(filtered_results)
        print(f"[Hard Project Filter] {after}/{before} entries match projects_in_focus={projects_in_focus}")
        # Optionally print a sample of result IDs
        print("  IDs:", [entry.get("message_id")[:6] for entry in filtered_results[:5]])

    sorted_results = sorted(filtered_results, key=lambda x: x["score"], reverse=True)
    print("[Final Results] Top entries after blending/filtering:")
    for i, entry in enumerate(sorted_results[:5]):
        print(
            f"  Rank {i + 1}: id={entry.get('message_id')[:6]}..., "
            f"score={entry['score']:.3f}, "
            f"proj_id={entry.get('project_id')}, "
            f"proj_ids={entry.get('project_ids')}"
        )
    return sorted_results[:top_k]

def search_indexed_memories(
    query,
    collections_weights,  # e.g., {'main': 0.3, 'project_A': 0.7}
    top_k=10,
    **kwargs
):
    """
    Search multiple Qdrant collections, blend and score results by source.
    """
    results_by_collection = {}
    for collection, weight in collections_weights.items():
        res = search_indexed_memory(
            query=query,
            collection_name=collection,
            top_k=int(top_k * 2),  # Overfetch for dedupe later
            **kwargs
        )
        # Annotate each result with its source and weight for later blending
        for r in res:
            r["_collection"] = collection
            r["_weight"] = weight
        results_by_collection[collection] = res

    # Merge, dedupe by message_id, blend scores
    merged = {}
    for collection, results in results_by_collection.items():
        for r in results:
            mid = r["message_id"]
            # If duplicate, keep the one with highest weighted score
            weighted_score = r["score"] * r["_weight"]
            if mid not in merged or weighted_score > merged[mid]["_blended_score"]:
                r["_blended_score"] = weighted_score
                merged[mid] = r

    # Sort all merged by blended score
    deduped_sorted = sorted(merged.values(), key=lambda x: x["_blended_score"], reverse=True)
    # Return only top_k
    return deduped_sorted[:top_k]


# </editor-fold>



# --------------------------
# MuseCortex Interface
# --------------------------
# <editor-fold desc="🧠 MuseCortex Backends (Mongo + Local)">
try:
    from pymongo import MongoClient, ReturnDocument
    MONGO_ENABLED = True
except ImportError:
    MONGO_ENABLED = False

class MuseCortexInterface:
    def add_memory(self, layer, entry):
        raise NotImplementedError

    def edit_memory(self, layer, entry_id, updates):
        raise NotImplementedError

    def delete_memory(self, layer, entry_id):
        raise NotImplementedError

    def get_entries_by_type(self, type_name):
        raise NotImplementedError

    def get_entries(self, query=None):
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

    def get_doc(self, id):
        raise NotImplementedError

    def update_doc(self, doc_id, updated_fields):
        raise NotImplementedError

    def search_cortex_for_timely_reminders(self, window_minutes):
        raise NotImplementedError

class MongoCortexClient(MuseCortexInterface):
    def __init__(self):
        uri = muse_config.get("MONGO_URI")
        self.client = MongoClient(uri)
        self.db = self.client["muse_memory"]
        self.collection = self.db["muse_cortex"]

    def add_memory(self, layer: str, entry: dict):
        # applies charter rules, timestamps, etc
        return mongo[layer].insert_one(entry)

    def edit_memory(self, layer: str, entry_id: str, updates: dict):
        updates["last_updated"] = datetime.utcnow().isoformat()
        return mongo[layer].update_one({"id": entry_id}, {"$set": updates})

    def delete_memory(self, layer: str, entry_id: str):
        return mongo[layer].delete_one({"id": entry_id})

    def get_entries_by_type(self, type_name):
        return list(self.collection.find({"type": type_name}))

    def get_entries(self, query=None):
        if query is None:
            query = {}
        return list(self.collection.find(query))

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

    def get_doc(self, doc_id):
        doc = self.collection.find_one({"id": doc_id})
        if not doc:
            # Optionally, initialize a new doc if not found
            doc = {"id": doc_id, "entries": []}
            self.collection.insert_one(doc)
        return doc

    def update_doc(self, doc_id, updated_fields):
        # Only updating the 'entries' field as per your handler
        updated = self.collection.find_one_and_update(
            {"id": doc_id},
            {"$set": updated_fields},
            return_document=ReturnDocument.AFTER
        )
        return updated

    def search_cortex_for_timely_reminders(self, window_minutes=0.5):
        user_tz = ZoneInfo(muse_config.get("USER_TIMEZONE"))  # e.g., "America/New_York"
        now_local = datetime.now(user_tz)
        lower_bound = now_local - timedelta(minutes=window_minutes)
        upper_bound = now_local + timedelta(minutes=window_minutes)

        reminders = self.get_entries_by_type("reminder")
        triggered = []

        for entry in reminders:
            cron = align_cron_for_croniter(entry.get("cron"))
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

class MemoryLayerManager:
    def __init__(self, cortex, utils):
        self.cortex = cortex
        self.utils = utils

    def add_entry(self, doc_id, entry):
        now = datetime.utcnow()
        entry['id'] = self.utils.generate_new_id()
        entry['created_on'] = now
        entry['updated_on'] = now
        doc = self.cortex.get_doc(doc_id)
        doc['entries'].append(entry)
        self.cortex.update_doc(doc_id, doc)
        self._log("add_entry", f"Added entry {entry['id']} to {doc_id}")
        # Only index semantically relevant layers
        if doc_id not in ("inner_monologue", "reminders"):
            asyncio.create_task(index_memory_queue.put(entry['id']))
        return entry

    def edit_entry(self, doc_id, entry_id, fields):
        doc = self.cortex.get_doc(doc_id)
        entry_map = {e['id']: (i, e) for i, e in enumerate(doc['entries'])}
        if entry_id not in entry_map:
            self._warn("edit_entry_failed", f"Missing ID {entry_id}")
            return None
        idx, entry = entry_map[entry_id]
        entry.update(fields)
        entry['updated_on'] = datetime.utcnow()
        doc['entries'][idx] = entry
        self.cortex.update_doc(doc_id, doc)
        self._log("edit_entry", f"Edited entry {entry_id} in {doc_id}")
        if doc_id not in ("inner_monologue", "reminders"):
            asyncio.create_task(index_memory_queue.put(entry['id']))
        return entry

    def recycle_entry(self, doc_id, entry_id):
        return self.edit_entry(doc_id, entry_id, {"is_deleted": True})

    def pin_entry(self, doc_id, entry_id):
        return self.edit_entry(doc_id, entry_id, {"is_pinned": True})

    def delete_entry(self, doc_id, entry_id):
        doc = self.cortex.get_doc(doc_id)
        new_entries = [e for e in doc['entries'] if e['id'] != entry_id]
        if len(new_entries) == len(doc['entries']):
            self._warn("delete_entry_failed", f"Missing ID {entry_id}")
            return False
        doc['entries'] = new_entries
        self.cortex.update_doc(doc_id, doc)
        self._log("delete_entry", f"Deleted entry {entry_id} from {doc_id}")
        if doc_id not in ("inner_monologue", "reminders"):
            delete_point(entry_id, "muse_memory_layers")
        return True

    def _log(self, action, text):
        self.utils.write_system_log(
            level="info", module="core", component="memory_core",
            function="MemoryLayerManager", action=action, text=text
        )

    def _warn(self, action, text):
        self.utils.write_system_log(
            level="warn", module="core", component="memory_core",
            function="MemoryLayerManager", action=action, text=text
        )

manager = MemoryLayerManager(cortex, utils)