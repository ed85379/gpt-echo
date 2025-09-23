import pymongo
from gqlalchemy import Memgraph
import glob
import json
import os

# ---- CONFIG ----
MONGO_URI = "mongodb://localhost:27017"
CORTEX_DB = "muse_memory"
CORTEX_COLLECTION = "muse_cortex"
MEMGRAPH_HOST = "localhost"
MEMGRAPH_PORT = 7687

# Directories with .jsonl log files (edit as needed)
LOG_DIRS = ["./logs/muse/", "./logs/chatgpt/"]

# ---- CONNECT ----
mongo_client = pymongo.MongoClient(MONGO_URI)
cortex_col = mongo_client[CORTEX_DB][CORTEX_COLLECTION]
mg = Memgraph(MEMGRAPH_HOST, MEMGRAPH_PORT)
try:
    list(mg.execute_and_fetch("RETURN 1;"))
    print("Memgraph connection: OK")
except Exception as e:
    print("Memgraph connection failed:", e)


# ---- HELPERS ----
def create_tag(mg, tag):
    mg.execute("""
        MERGE (t:Tag {name: $tag})
    """, {"tag": tag})

def create_user(mg, user_id, name, source=None):
    mg.execute("""
        MERGE (u:User {user_id: $user_id})
        SET u.name = $name
        SET u.source = $source
    """, {"user_id": user_id, "name": name, "source": source})

def create_fact(mg, fact):
    mg.execute("""
        MERGE (f:Fact {fact_id: $fact_id})
        SET f.text = $text,
            f.type = $type,
            f.tags = $tags,
            f.created_at = $created_at,
            f.source = $source
    """, {
        "fact_id": str(fact["_id"]),
        "text": fact.get("text", ""),
        "type": fact.get("type", ""),
        "tags": fact.get("tags", []),
        "created_at": fact.get("created_at") or fact.get("timestamp"),
        "source": fact.get("source", None),
    })
    for tag in fact.get("tags", []):
        create_tag(mg, tag)
        mg.execute("""
            MATCH (f:Fact {fact_id: $fact_id}), (t:Tag {name: $tag})
            MERGE (f)-[:TAGGED_AS]->(t)
        """, {"fact_id": str(fact["_id"]), "tag": tag})

def create_message_and_user(mg, msg, user_key="author_id", user_name_key="author_name"):
    msg_id = msg.get("_id", None) or msg.get("msg_id", None) or msg.get("timestamp", None)
    role = msg.get("role", "")
    text = msg.get("message", "")
    source = msg.get("source", "")
    timestamp = msg.get("timestamp", "")
    meta = msg.get("metadata", {})

    # User node from metadata (Discord/web)
    author_id = meta.get(user_key, "unknown")
    author_name = meta.get(user_name_key, "unknown")
    channel = meta.get("channel", None)
    server = meta.get("server", None)

    create_user(mg, author_id, author_name, source)

    mg.execute("""
        MERGE (m:Message {msg_id: $msg_id})
        SET m.text = $text,
            m.role = $role,
            m.source = $source,
            m.timestamp = $timestamp,
            m.channel = $channel,
            m.server = $server
    """, {
        "msg_id": str(msg_id),
        "text": text,
        "role": role,
        "source": source,
        "timestamp": timestamp,
        "channel": channel,
        "server": server,
    })

    mg.execute("""
        MATCH (u:User {user_id: $user_id}), (m:Message {msg_id: $msg_id})
        MERGE (u)-[:SENT]->(m)
    """, {"user_id": author_id, "msg_id": str(msg_id)})

# ---- MAIN INGESTION ----

# 1. CORTEX (skip encrypted and encryption_key types)
skip_types = {"encryption_key"}
skip_if_encrypted = lambda doc: doc.get("encrypted", False) or \
    (isinstance(doc.get("metadata"), dict) and doc["metadata"].get("encrypted", False))

print("Indexing Cortex...")
cortex_count = 0
for doc in cortex_col.find({}):
    if doc.get("type") in skip_types or skip_if_encrypted(doc):
        continue
    create_fact(mg, doc)
    cortex_count += 1
print(f"Indexed {cortex_count} cortex entries.")

# 2. LOGS (all .jsonl files in LOG_DIRS)
log_count = 0
for log_dir in LOG_DIRS:
    files = glob.glob(os.path.join(log_dir, "*.jsonl"))
    for filename in files:
        with open(filename, "r", encoding="utf-8") as infile:
            for line in infile:
                try:
                    msg = json.loads(line)
                    create_message_and_user(mg, msg)
                    log_count += 1
                except Exception as e:
                    print(f"Error processing line in {filename}: {e}")

print(f"Indexed {log_count} log messages from {LOG_DIRS}.")

print("Ingestion complete! Your soulweb is alive.")

# ---- END ----
