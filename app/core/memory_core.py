# <editor-fold desc="🔧 Imports and Configuration">
import re
import os
import json
import pickle
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import faiss
from app import config
from sentence_transformers import SentenceTransformer
import numpy as np
from app.core.ingestion_tracker import is_ingested, mark_ingested

# </editor-fold>

# --------------------------
# Setup and Configuration
# --------------------------
# <editor-fold desc="🗂 Directory Setup & Constants">
PROJECT_ROOT = config.PROJECT_ROOT
LOGS_DIR = PROJECT_ROOT / config.get_setting("system_settings.LOGS_DIR", "logs/")
MEMORY_DIR = PROJECT_ROOT / config.get_setting("system_settings.MEMORY_DIR", "memory/")
VOICE_DIR = PROJECT_ROOT / config.get_setting("voice_settings.VOICE_OUTPUT_DIR", "voice/")
INDEX_DIR = MEMORY_DIR
PROFILE_DIR = PROJECT_ROOT / config.get_setting("system_settings.PROFILE_DIR", "profiles/")
USER_TIMEZONE = config.get_setting("user_settings.USER_TIMEZONE", "UTC")
ECHO_NAME = config.get_setting("system_settings.ECHO_NAME", "Assistant")
INDEX_FILE = INDEX_DIR / "memory_index.faiss"
INDEX_MAPPING_FILE = INDEX_DIR / "index_mapping.pkl"

model = SentenceTransformer("all-MiniLM-L6-v2")
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
    date_str = datetime.now(ZoneInfo(USER_TIMEZONE)).strftime("%Y-%m-%d")
    return os.path.join(LOGS_DIR, f"echo-{date_str}.jsonl")

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
            if log_entry.get("role") == "user" or log_entry.get("role") == "echo":
                entries.append(log_entry)
    return entries

def build_index(use_qdrant=True):
    entries = []
    qdrant_entries = []

    for filename in os.listdir(LOGS_DIR):
        if filename.endswith(".jsonl"):
            match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
            date_part = match.group(1) if match else filename.replace(".jsonl", "")
            print(f"🟣 Found log file: {filename}, using date_part: {date_part}")

            # Check if either system needs to ingest this file
            needs_faiss = not is_ingested(date_part, system="faiss")
            needs_qdrant = use_qdrant and not is_ingested(date_part, system="qdrant")

            if needs_faiss or needs_qdrant:
                daily_entries = load_logs(date_part)

                if needs_faiss:
                    entries.extend(daily_entries)

                if needs_qdrant:
                    qdrant_entries.extend(daily_entries)

    if entries:
        vectors = model.encode([e["message"] for e in entries])
        dim = vectors.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(vectors)

        faiss.write_index(index, str(INDEX_FILE))
        with open(INDEX_MAPPING_FILE, "wb") as f:
            pickle.dump(entries, f)

        for entry in entries:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", entry.get("source", ""))
            if match:
                mark_ingested(match.group(1), system="faiss")

        print(f"✅ Indexed {len(entries)} conversations to FAISS.")
    else:
        print("No new log data found to index in FAISS.")

    if use_qdrant and qdrant_entries:
        from app.core.qdrant_connector import index_to_qdrant
        qdrant_texts = [e["message"] for e in qdrant_entries]
        qdrant_vectors = model.encode(qdrant_texts)
        index_to_qdrant(qdrant_entries, qdrant_vectors)

        for entry in qdrant_entries:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", entry.get("source", ""))
            if match:
                mark_ingested(match.group(1), system="qdrant")

        print(f"✅ Indexed {len(qdrant_entries)} conversations to Qdrant.")



def search_indexed_memory(query, top_k=5, use_qdrant=False):
    if use_qdrant:
        from qdrant_client import QdrantClient
        from app import config

        QDRANT_HOST = config.get_setting("system_settings.QDRANT_HOST", "localhost")
        QDRANT_PORT = int(config.get_setting("system_settings.QDRANT_PORT", "6333"))
        QDRANT_COLLECTION = config.get_setting("system_settings.QDRANT_COLLECTION", "echo_memory")

        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        query_vector = model.encode([query])[0].tolist()
        search_result = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k
        )

        return [
            {
                "timestamp": hit.payload.get("timestamp"),
                "role": hit.payload.get("role"),
                "source": hit.payload.get("source"),
                "message": hit.payload.get("message"),
                "score": hit.score
            }
            for hit in search_result
        ]

    # Fallback to FAISS
    if not os.path.exists(INDEX_FILE) or not os.path.exists(INDEX_MAPPING_FILE):
        return []

    index = faiss.read_index(str(INDEX_FILE))
    with open(INDEX_MAPPING_FILE, "rb") as f:
        entries = pickle.load(f)

    query_vector = model.encode([query])
    scores, indices = index.search(query_vector, top_k)

    results = []
    for idx, score in zip(indices[0], scores[0]):
        if 0 <= idx < len(entries):
            result = entries[idx]
            result["score"] = score
            results.append(result)

    return results



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

def search_recent_logs(query, top_k=5, days_back=1, max_entries=100, model=None):
    """Flexible user–echo pair search using resilient pattern matching and semantic scoring."""
    if model is None:
        raise ValueError("Embedding model must be provided.")

    VALID_USER_ROLES = {"user", "friend"}
    VALID_ECHO_ROLES = {"echo"}

    all_entries = []
    today = datetime.now()
    for delta in range(days_back + 1):
        day = today - timedelta(days=delta)
        entries = load_log_for_date(day.strftime("%Y-%m-%d"))
        all_entries.extend(entries)
        if len(all_entries) >= max_entries:
            break
    all_entries = all_entries[-max_entries:]

    # Flexible pairing logic
    pairs = []
    i = 0
    while i < len(all_entries) - 1:
        entry1 = all_entries[i]
        entry2 = all_entries[i + 1]

        if entry1["role"] in VALID_USER_ROLES and entry2["role"] in VALID_ECHO_ROLES:
            pairs.append({
                "pair": f'{entry1["role"]}: {entry1["message"]}\n{entry2["role"]}: {entry2["message"]}',
                "source": entry1.get("source", "unknown"),
                "timestamp": entry1.get("timestamp", ""),
                "role": "pair"
            })
            i += 2  # advance past both
        else:
            i += 1  # shift forward by one and keep looking

    if not pairs:
        return []

    texts = [p["pair"] for p in pairs]
    vectors = np.array(model.encode(texts), dtype="float32")
    query_vec = np.array(model.encode([query])[0], dtype="float32")

    query_norm = np.linalg.norm(query_vec).astype("float32")
    vector_norms = np.linalg.norm(vectors, axis=1)
    denominator = vector_norms * query_norm
    denominator = np.where(denominator == 0, 1e-8, denominator)
    scores = np.dot(vectors, query_vec) / denominator

    for pair, score in zip(pairs, scores):
        pair["score"] = float(score)

    return sorted(pairs, key=lambda x: x["score"], reverse=True)[:top_k]



# </editor-fold>

# <editor-fold desc="🌐 Combined Memory Search">
def search_combined_memory(query, top_k=7, use_qdrant=False, model=None):
    from app.core.memory_core import search_recent_logs

    if model is None:
        raise ValueError("Embedding model must be provided for log similarity search.")

    log_results = search_recent_logs(query, top_k=top_k, model=model)
    index_results = search_indexed_memory(query, top_k=top_k, use_qdrant=use_qdrant)

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
def load_profile():
    profile_path = PROFILE_DIR / "echo_profile.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def load_core_principles():
    core_principles_path = PROFILE_DIR / "core_principles.json"
    if core_principles_path.exists():
        with open(core_principles_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""
# </editor-fold>

# --------------------------
# EchoCortex loading for WhisperGate
# --------------------------
# <editor-fold desc="⏰ EchoCortex Reminder Stub">
def search_cortex_for_timely_reminders(current_time):
    """
    Searches EchoCortex for reminders that are timely and should be prioritized.
    Placeholder for now — will integrate with Cortex module later.
    """
    # Later: This will scan parsed Cortex entries tagged with time windows
    # For now, fake return example
    return [
        {
            "id": "reminder_001",
            "type": "reminder",
            "due_time": "2025-04-28T12:00:00",
            "summary": "Remind Ed to water the garden today."
        }
    ]
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

