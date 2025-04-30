# memory_core.py

import os
import json
import pickle
from datetime import datetime
from zoneinfo import ZoneInfo
import faiss
from app import config
from sentence_transformers import SentenceTransformer
import numpy as np

# --------------------------
# Setup and Configuration
# --------------------------

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

# --------------------------
# Chronicle Logging
# --------------------------

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


# --------------------------
# Ingestion Tracking
# --------------------------

def load_flags():
    flags_path = INDEX_DIR / "ingested_flags.json"
    if flags_path.exists():
        with open(flags_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_flags(flags):
    flags_path = INDEX_DIR / "ingested_flags.json"
    with open(flags_path, "w", encoding="utf-8") as f:
        json.dump(flags, f)

def mark_ingested(date_str):
    flags = load_flags()
    flags[date_str] = True
    save_flags(flags)

def is_ingested(date_str):
    flags = load_flags()
    return flags.get(date_str, False)

# --------------------------
# Memory Vector Indexing
# --------------------------

def load_logs(date_str):
    log_path = os.path.join(LOGS_DIR, f"echo-{date_str}.jsonl")
    if not os.path.exists(log_path):
        return []
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            log_entry = json.loads(line)
            if log_entry.get("role") == "user" or log_entry.get("role") == "echo":
                entries.append(log_entry["message"])
    return entries

def build_index():
    entries = []
    for filename in os.listdir(LOGS_DIR):
        if filename.endswith(".jsonl"):
            date_part = filename.split("-")[-1].replace(".jsonl", "")
            if not is_ingested(date_part):
                daily_entries = load_logs(date_part)
                entries.extend(daily_entries)
                mark_ingested(date_part)
    if not entries:
        print("No new log data found to index.")
        return

    vectors = model.encode(entries)
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    faiss.write_index(index, str(INDEX_FILE))
    with open(INDEX_MAPPING_FILE, "wb") as f:
        pickle.dump(entries, f)

    print(f"Indexed {len(entries)} conversations.")

def search_indexed_memory(query, top_k=5):
    if not os.path.exists(INDEX_FILE) or not os.path.exists(INDEX_MAPPING_FILE):
        return []

    index = faiss.read_index(str(INDEX_FILE))
    with open(INDEX_MAPPING_FILE, "rb") as f:
        entries = pickle.load(f)

    query_vector = model.encode([query])
    scores, indices = index.search(query_vector, top_k)

    results = []
    for idx in indices[0]:
        if 0 <= idx < len(entries):
            results.append(entries[idx])
    return results



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

def search_combined_memory(query, top_k=7):
    log_results = search_today_log(query, top_k=top_k)
    index_results = search_indexed_memory(query, top_k=top_k)
    combined = log_results + [r for r in index_results if r not in log_results]
    return combined[:top_k]


# --------------------------
# Profile and Memory Root Loading
# --------------------------

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

# --------------------------
# EchoCortex loading for WhisperGate
# --------------------------

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

# --------------------------
# EchoCortex Interface
# --------------------------

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


# --------------------------
# Cortex Loader
# --------------------------

def get_cortex():
    if MONGO_ENABLED:
        try:
            return MongoCortexClient()
        except Exception as e:
            print(f"Mongo unavailable: {e}")
    return LocalCortexClient()


# Global instance
cortex = get_cortex()
