# <editor-fold desc="🔧 Imports and Configuration">
import re
import os
import json
import pickle
from datetime import datetime, timedelta
from dateutil.parser import isoparse
from zoneinfo import ZoneInfo
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
from app import config
from app.core import utils


# </editor-fold>

# --------------------------
# Setup and Configuration
# --------------------------
# <editor-fold desc="🗂 Directory Setup & Constants">
PROJECT_ROOT = config.PROJECT_ROOT
USE_QDRANT = config.USE_QDRANT
LOGS_DIR = config.LOGS_DIR
CHATGPT_LOGS_DIR = config.CHATGPT_LOGS_DIR
MEMORY_DIR = config.MEMORY_DIR
INDEX_DIR = MEMORY_DIR
PROFILE_DIR = config.PROFILE_DIR
USER_TIMEZONE = config.USER_TIMEZONE
ECHO_NAME = config.ECHO_NAME
INDEX_FILE = INDEX_DIR / "memory_index.faiss"
INDEX_MAPPING_FILE = INDEX_DIR / "index_mapping.pkl"
VALID_ROLES = {"user", "echo", "friend"}
model = SentenceTransformer(config.SENTENCE_TRANSFORMER_MODEL)
# </editor-fold>

# --------------------------
# Chronicle Logging
# --------------------------
# <editor-fold desc="📝 Logging Functions">
def log_message(role, content, source="frontend", metadata=None):
    """
    Log a message from any source into the Echo system.

    Args:
        role (str): 'echo', 'user', 'friend', or 'other'
        content (str): The actual message content
        source (str): 'frontend', 'discord', 'sms', 'speaker', etc.
        metadata (dict, optional): Additional context info about the message
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now(ZoneInfo(USER_TIMEZONE)).isoformat()

    log_entry = {
        "timestamp": timestamp,
        "role": role,
        "source": source,
        "message": content,
        "metadata": metadata or {}
    }

    with open(get_log_filename(), "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def get_log_filename():
    utc_date_str = datetime.utcnow().strftime("%Y-%m-%d")
    return os.path.join(LOGS_DIR, f"echo-{utc_date_str}.jsonl")

def read_today_log():
    path = get_log_filename()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line.strip()) for line in f if line.strip()]

# </editor-fold>

# --------------------------
# Memory Vector Indexing
# --------------------------
# <editor-fold desc="📚 Memory Vector Indexing">
def load_logs(date_str):
    log_path = os.path.join(LOGS_DIR, f"echo-{date_str}.jsonl")
    if not os.path.exists(log_path):
        return []
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            log_entry = json.loads(line)
            if log_entry.get("role") in VALID_ROLES:
                entries.append(log_entry)
    return entries

def load_logs_from_path(log_path):
    if not os.path.exists(log_path):
        return []
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                log_entry = json.loads(line)
                if log_entry.get("role") in VALID_ROLES:
                    entries.append(log_entry)
            except Exception:
                continue
    return entries


def build_index(use_qdrant=USE_QDRANT, dryrun=False):
    from app.core.ingestion_tracker import is_ingested, mark_ingested
    from app.databases.qdrant_connector import index_to_qdrant

    echo_entries = []
    chatgpt_entries = []
    qdrant_echo_entries = []
    qdrant_chatgpt_entries = []

    seen_filenames = set()
    today_utc = datetime.utcnow().strftime("%Y-%m-%d")

    def process_logs(log_dir, source_label, entry_collector, qdrant_collector, manifest_key):
        for filename in os.listdir(log_dir):
            if not filename.endswith(".jsonl"):
                continue
            if filename in seen_filenames:
                continue
            seen_filenames.add(filename)

            match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
            if not match:
                continue
            date_part = match.group(1)
            if date_part == today_utc:
                continue  # Skip today’s logs to avoid partial ingestion

            print(f"🟣 Checking {source_label} log file: {filename} for date: {date_part}")

            needs_faiss = not is_ingested(filename, system="faiss", log_type=manifest_key)
            needs_qdrant = use_qdrant and not is_ingested(filename, system="qdrant", log_type=manifest_key)

            if needs_faiss or needs_qdrant:
                log_path = os.path.join(log_dir, filename)
                daily_entries = load_logs_from_path(log_path)
                print(f"📝 Found {len(daily_entries)} entries for {date_part}")

                if needs_faiss:
                    entry_collector.extend(daily_entries)
                    if not dryrun:
                        mark_ingested(filename, system="faiss", log_type=manifest_key)

                if needs_qdrant:
                    qdrant_collector.extend(daily_entries)
                    if not dryrun:
                        mark_ingested(filename, system="qdrant", log_type=manifest_key)

    process_logs(LOGS_DIR, "Echo", echo_entries, qdrant_echo_entries, "echo")
    process_logs(CHATGPT_LOGS_DIR, "ChatGPT", chatgpt_entries, qdrant_chatgpt_entries, "chatgpt")

    if dryrun:
        print(f"💡 [Dry Run] Would index {len(echo_entries)} Echo entries and {len(chatgpt_entries)} ChatGPT entries to FAISS.")
        print(f"💡 [Dry Run] Would index {len(qdrant_echo_entries)} Echo entries and {len(qdrant_chatgpt_entries)} ChatGPT entries to Qdrant.")
        return

    all_faiss_entries = echo_entries + chatgpt_entries
    if all_faiss_entries:
        vectors = model.encode([e["message"] for e in all_faiss_entries])
        dim = vectors.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(vectors)

        faiss.write_index(index, str(INDEX_FILE))
        with open(INDEX_MAPPING_FILE, "wb") as f:
            pickle.dump(all_faiss_entries, f)

        print(f"✅ Indexed {len(all_faiss_entries)} total entries to FAISS.")
    else:
        print("📭 No new log data found to index in FAISS.")

    all_qdrant_entries = qdrant_echo_entries + qdrant_chatgpt_entries
    if use_qdrant and all_qdrant_entries:
        qdrant_texts = [e["message"] for e in all_qdrant_entries]
        qdrant_vectors = model.encode(qdrant_texts)
        index_to_qdrant(all_qdrant_entries, qdrant_vectors)

        print(f"✅ Indexed {len(all_qdrant_entries)} total entries to Qdrant.")


def search_indexed_memory(
    query,
    top_k=5,
    use_qdrant=False,
    bias_author_id=None,
    bias_source=None,
    score_boost=0.1,
    source_boost=0.1,
    penalize_echo=True,
    echo_penalty=0.05
):
    """
    Search indexed memory via Qdrant or FAISS.

    Parameters:
    - query (str): Search query.
    - top_k (int): Number of top results to return.
    - use_qdrant (bool): Whether to use Qdrant instead of FAISS.
    - bias_author_id (str|None): Optional. Boost results by this author.
    - bias_source (str|None): Optional. Boost results from this source (e.g., 'discord').
    - score_boost (float): Score boost for matching author_id.
    - source_boost (float): Score boost for matching source.
    - penalize_echo (bool): If True, apply a penalty to Echo's own messages.
    - echo_penalty (float): Score penalty for Echo's own responses.

    Returns:
    - List[dict]: Ranked search results.
    """
    query_vector = model.encode([query])[0]

    if use_qdrant:
        from qdrant_client import QdrantClient
        from app import config

        QDRANT_HOST = config.get_setting("system_settings.QDRANT_HOST", "localhost")
        QDRANT_PORT = int(config.get_setting("system_settings.QDRANT_PORT", "6333"))
        QDRANT_COLLECTION = config.get_setting("system_settings.QDRANT_COLLECTION", "echo_memory")

        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        search_result = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector.tolist(),
            limit=top_k
        )

        results = []
        for hit in search_result:
            entry = {
                "timestamp": hit.payload.get("timestamp"),
                "role": hit.payload.get("role"),
                "source": hit.payload.get("source"),
                "message": hit.payload.get("message"),
                "metadata": hit.payload.get("metadata", {}),
                "score": hit.score
            }

            if bias_author_id and entry["metadata"].get("author_id") == bias_author_id:
                entry["score"] += score_boost
            if bias_source and entry.get("source") == bias_source:
                entry["score"] += source_boost
            if penalize_echo and entry.get("role") == "echo":
                entry["score"] -= echo_penalty

            results.append(entry)

        return sorted(results, key=lambda x: x["score"], reverse=True)

    # FAISS fallback
    if not os.path.exists(INDEX_FILE) or not os.path.exists(INDEX_MAPPING_FILE):
        return []

    index = faiss.read_index(str(INDEX_FILE))
    with open(INDEX_MAPPING_FILE, "rb") as f:
        entries = pickle.load(f)

    scores, indices = index.search(np.array([query_vector]), top_k)

    results = []
    for idx, score in zip(indices[0], scores[0]):
        if 0 <= idx < len(entries):
            entry = entries[idx]
            entry["score"] = float(score)

            if bias_author_id and entry["metadata"].get("author_id") == bias_author_id:
                entry["score"] += score_boost
            if bias_source and entry.get("source") == bias_source:
                entry["score"] += source_boost
            if penalize_echo and entry.get("role") == "echo":
                entry["score"] -= echo_penalty

            results.append(entry)

    return sorted(results, key=lambda x: x["score"], reverse=True)




# </editor-fold>

# <editor-fold desc="🕰️ Log-Based Memory Search (Recent + Today)">
def search_today_log(query, top_k=5):
    log_entries = read_today_log()
    pairs = [
        f'User: {log_entries[i]["message"]}\n{ECHO_NAME}: {log_entries[i + 1]["message"]}'
        for i in range(0, len(log_entries) - 1, 2)
        if log_entries[i]["role"] == "user" and log_entries[i + 1]["role"] == "echo"
    ]
    if not pairs:
        return []

    vectors = np.array(model.encode(pairs), dtype="float32")
    query_vec = np.array(model.encode([query])[0], dtype="float32")

    query_norm = np.linalg.norm(query_vec).astype("float32")
    vector_norms = np.linalg.norm(vectors, axis=1)
    denominator = vector_norms * query_norm
    denominator = np.where(denominator == 0, 1e-8, denominator)

    scores = np.dot(vectors, query_vec) / denominator
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [pairs[i] for i in top_indices]


def load_log_for_date(date_str):
    filename = f"echo-{date_str}.jsonl"
    log_path = LOGS_DIR / filename
    entries = []
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("role") in ("user", "echo"):
                        entries.append(entry)
                except Exception:
                    continue
    return entries

def search_recent_logs(query, top_k=5, days_back=1, max_entries=100, model=None, bias_source=None, bias_author_id=None, score_boost=0.05):
    """Semantic search over individual log messages with optional author bias and embedded identity awareness."""
    if model is None:
        raise ValueError("Embedding model must be provided.")

    all_entries = []
    today = datetime.now()
    for delta in range(days_back + 1):
        day = today - timedelta(days=delta)
        entries = load_log_for_date(day.strftime("%Y-%m-%d"))
        all_entries.extend(entries)
        if len(all_entries) >= max_entries:
            break

    all_entries = all_entries[-max_entries:]  # truncate to max_entries

    # Filter for meaningful roles only
    entries = [e for e in all_entries if e["role"] in {"user", "friend", "echo"}]

    # Embed message text **with author label** (e.g., "Ed: That’s brilliant.")
    labeled_texts = [
        f'{e.get("metadata", {}).get("author_name", e["role"]).strip()}: {e["message"].strip()}'
        for e in entries
    ]

    vectors = np.array(model.encode(labeled_texts), dtype="float32")
    query_vec = np.array(model.encode([query])[0], dtype="float32")

    query_norm = np.linalg.norm(query_vec).astype("float32")
    vector_norms = np.linalg.norm(vectors, axis=1)
    denominator = vector_norms * query_norm
    denominator = np.where(denominator == 0, 1e-8, denominator)
    scores = np.dot(vectors, query_vec) / denominator

    results = []
    for entry, labeled_text, score in zip(entries, labeled_texts, scores):
        if bias_author_id and entry.get("metadata", {}).get("author_id") == bias_author_id:
            score += score_boost
        entry["score"] = float(score)
        entry["labeled_text"] = labeled_text  # Optional: keep for reference
        results.append(entry)

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]



# </editor-fold>

# <editor-fold desc="🌐 Combined Memory Search">
def search_combined_memory(
    query,
    top_k=5,
    use_qdrant=False,
    bias_author_id=None,
    bias_source=None,
    score_boost=0.05,
    source_boost=0.05,
    penalize_echo=True,
    echo_penalty=0.05,
    model=None
):
    from app.core.memory_core import search_recent_logs

    if model is None:
        raise ValueError("Embedding model must be provided for log similarity search.")

    log_results = search_recent_logs(query, top_k=top_k, model=model)
    index_results = search_indexed_memory(
        query,
        top_k=top_k,
        use_qdrant=use_qdrant,
        bias_author_id=bias_author_id,
        bias_source=bias_source,
        score_boost=score_boost,
        source_boost=source_boost,
        penalize_echo=penalize_echo,
        echo_penalty=echo_penalty
    )

    # De-dupe by (timestamp, message) combo
    seen = set()
    combined = []
    for result in log_results + index_results:
        key = (result.get("timestamp"), result.get("message"))
        if key not in seen:
            combined.append(result)
            seen.add(key)

    return combined[:top_k]
# </editor-fold>

# --------------------------
# Profile and Memory Root Loading
# --------------------------
# <editor-fold desc="👤 Profile and Principle Loaders">
def load_profile(subset: list[str] = None, as_dict: bool = False):
    profile_path = PROFILE_DIR / "echo_profile.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if subset:
                data = {key: data[key] for key in subset if key in data}
            return data if as_dict else json.dumps(data, ensure_ascii=False, indent=2)
    return {} if as_dict else ""


def load_core_principles():
    core_principles_path = PROFILE_DIR / "core_principles.json"
    if core_principles_path.exists():
        with open(core_principles_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""
# </editor-fold>


# --------------------------
# EchoCortex Interface
# --------------------------
# <editor-fold desc="🧠 EchoCortex Backends (Mongo + Local)">
try:
    from pymongo import MongoClient
    MONGO_ENABLED = True
except ImportError:
    MONGO_ENABLED = False

class EchoCortexInterface:
    def get_entries_by_type(self, type_name):
        raise NotImplementedError

    def add_entry(self, entry):
        raise NotImplementedError

    def get_all_entries(self):
        raise NotImplementedError

    def search_by_tag(self, tag):
        raise NotImplementedError

    def search_cortex_for_timely_reminders(self, window_minutes):
        raise NotImplementedError

class MongoCortexClient(EchoCortexInterface):
    def __init__(self):
        uri = config.get_setting("memory_settings.MONGO_URI")
        self.client = MongoClient(uri)
        self.db = self.client["echo_memory"]
        self.collection = self.db["echo_cortex"]

    def get_entries_by_type(self, type_name):
        return list(self.collection.find({"type": type_name}))

    def add_entry(self, entry):
        entry["created_at"] = datetime.utcnow().isoformat()
        self.collection.insert_one(entry)

    def get_all_entries(self):
        return list(self.collection.find())

    def search_by_tag(self, tag):
        return list(self.collection.find({"tags": tag}))

    def search_cortex_for_timely_reminders(self, window_minutes=1):
        now = datetime.now(ZoneInfo(config.USER_TIMEZONE))
        lower_bound = now - timedelta(minutes=window_minutes)
        upper_bound = now + timedelta(minutes=window_minutes)

        reminders = self.get_entries_by_type("reminder")
        triggered = []

        def is_within_window(when):
            return lower_bound <= when <= upper_bound

        def repeating_should_trigger(entry):
            repeat = entry.get("repeat")
            remind_at = entry.get("remind_at")
            ends_on = entry.get("ends_on")

            try:
                base_time = utils.parse_remind_time(remind_at)
                if base_time is None:
                    return False

                if ends_on:
                    ends = isoparse(ends_on).astimezone(ZoneInfo(config.USER_TIMEZONE))
                    if now > ends:
                        return False

                # Match hour + minute only
                base_hm = (base_time.hour, base_time.minute)
                now_hm = (now.hour, now.minute)

                if base_hm != now_hm:
                    return False

                weekday = now.weekday()  # 0 = Monday, 6 = Sunday

                if repeat == "daily":
                    return True
                elif repeat == "weekdays":
                    return weekday < 5
                elif repeat == "weekly":
                    # Support explicit day matching
                    repeat_on = entry.get("repeat_on")
                    if repeat_on:
                        now_day = now.strftime("%A").lower()
                        return now_day == repeat_on.lower()
                    else:
                        # Fallback: assume the weekday of base_time
                        return weekday == base_time.weekday()

            except Exception as e:
                print(f"Error parsing repeating reminder: {e}")
                return False

            return False

        for entry in reminders:
            try:
                raw_time = entry.get("remind_at")
                when = utils.parse_remind_time(raw_time)
                # One-time trigger
                if not entry.get("repeat"):
                    if is_within_window(when):
                        triggered.append(entry)

                # Repeating logic
                elif repeating_should_trigger(entry):
                    # Create a virtual instance of this reminder for right now
                    virtual_entry = entry.copy()
                    virtual_entry["triggered_at"] = now.isoformat()
                    triggered.append(virtual_entry)

            except Exception as e:
                print(f"Reminder check error: {e}")
        print(f"✅ Found {len(triggered)} reminders ready to fire.")

        return triggered


class LocalCortexClient(EchoCortexInterface):
    def __init__(self):
        self.file_path = MEMORY_DIR / "echo_cortex.jsonl"
        self.entries = []
        if self.file_path.exists():
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.entries = [json.loads(line) for line in f if line.strip()]

    def get_entries_by_type(self, type_name):
        return [e for e in self.entries if e.get("type") == type_name]

    def add_entry(self, entry):
        entry["created_at"] = datetime.utcnow().isoformat()
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.entries.append(entry)

    def get_all_entries(self):
        return self.entries

    def search_by_tag(self, tag):
        return [e for e in self.entries if tag in e.get("tags", [])]

    def search_cortex_for_timely_reminders(self, window_minutes=1):
        now = datetime.now(ZoneInfo(config.USER_TIMEZONE))
        lower_bound = now - timedelta(minutes=window_minutes)
        upper_bound = now + timedelta(minutes=window_minutes)

        reminders = self.get_entries_by_type("reminder")
        triggered = []

        def is_within_window(when):
            return lower_bound <= when <= upper_bound

        def repeating_should_trigger(entry):
            repeat = entry.get("repeat")
            remind_at = entry.get("remind_at")
            ends_on = entry.get("ends_on")

            try:
                base_time = utils.parse_remind_time(remind_at)
                if base_time is None:
                    return False

                if ends_on:
                    ends = isoparse(ends_on).astimezone(ZoneInfo(config.USER_TIMEZONE))
                    if now > ends:
                        return False

                # Match hour + minute only
                base_hm = (base_time.hour, base_time.minute)
                now_hm = (now.hour, now.minute)

                if base_hm != now_hm:
                    return False

                weekday = now.weekday()  # 0 = Monday, 6 = Sunday

                if repeat == "daily":
                    return True
                elif repeat == "weekdays":
                    return weekday < 5
                elif repeat == "weekly":
                    # Support explicit day matching
                    repeat_on = entry.get("repeat_on")
                    if repeat_on:
                        now_day = now.strftime("%A").lower()
                        return now_day == repeat_on.lower()
                    else:
                        # Fallback: assume the weekday of base_time
                        return weekday == base_time.weekday()

            except Exception as e:
                print(f"Error parsing repeating reminder: {e}")
                return False

            return False

        for entry in reminders:
            try:
                raw_time = entry.get("remind_at")
                when = utils.parse_remind_time(raw_time)

                # One-time trigger
                if not entry.get("repeat"):
                    if is_within_window(when):
                        triggered.append(entry)

                # Repeating logic
                elif repeating_should_trigger(entry):
                    # Create a virtual instance of this reminder for right now
                    virtual_entry = entry.copy()
                    virtual_entry["triggered_at"] = now.isoformat()
                    triggered.append(virtual_entry)

            except Exception as e:
                print(f"Reminder check error: {e}")

        return triggered


# </editor-fold>

# --------------------------
# Cortex Loader
# --------------------------
# <editor-fold desc="⚙️ Cortex Loader and Global Instance">
def get_cortex():
    if MONGO_ENABLED:
        try:
            return MongoCortexClient()
        except Exception as e:
            print(f"Mongo unavailable: {e}")
    return LocalCortexClient()


# Global instance
cortex = get_cortex()
# </editor-fold>

