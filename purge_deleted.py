import os
from pymongo import MongoClient
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointIdsList
from qdrant_client.http import models as qmodels
from gqlalchemy import Memgraph
import time
from app.databases.qdrant_connector import message_id_to_uuid

# --- CONFIG ---
MONGO_URI = "mongodb://localhost:27017/"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "muse_memory"  # Adjust if needed
MEMGRAPH_HOST = "localhost"
MEMGRAPH_PORT = 7687

DB_NAME = "muse_memory"
COLLECTION = "muse_conversations"

AUDIT_LOG = "purged_message_ids.txt"
FAILED_LOG = "failed_message_ids.txt"

# --- CONNECTIONS ---
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION]
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
memgraph = Memgraph(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)

# --- STEP 1: FIND IS_DELETED MESSAGES ---
deleted_msgs = list(collection.find({"is_deleted": True}))
print(f"Found {len(deleted_msgs)} messages marked for deletion.")

if not deleted_msgs:
    print("Nothing to purge. Exiting.")
    exit()

message_ids = [str(msg["message_id"]) for msg in deleted_msgs if "message_id" in msg]
successfully_purged = []
failed_upstream = []

def delete_qdrant(message_id):
    try:
        delete_id = message_id_to_uuid(message_id)
        selector = PointIdsList(points=[delete_id])  # Always a list!
        print("Selector:", selector)
        qdrant.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=selector,
            wait=True,
        )
        result = qdrant.retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=[delete_id],  # Also a list!
        )
        if not result or len(result) == 0:
            return True
        print(f"Qdrant: {message_id} still present after deletion attempt.")
        return False
    except Exception as e:
        print(f"Qdrant: Exception deleting {message_id}: {e}")
        return False

def delete_memgraph(message_id):
    try:
        query = f"MATCH (m:Message {{message_id: '{message_id}'}}) DETACH DELETE m;"
        memgraph.execute(query)
        # Confirm by checking node existence
        check_query = f"MATCH (m:Message {{message_id: '{message_id}'}}) RETURN m LIMIT 1;"
        check_result = memgraph.execute_and_fetch(check_query)
        if not list(check_result):  # Should be empty if deleted
            return True
        print(f"Memgraph: {message_id} still present after deletion attempt.")
        return False
    except Exception as e:
        print(f"Memgraph: Exception deleting {message_id}: {e}")
        return False

for mid in message_ids:
    print(f"\nPurging {mid}...")
    qdrant_ok = delete_qdrant(mid)
    memgraph_ok = delete_memgraph(mid)

    if qdrant_ok and memgraph_ok:
        # Delete from Mongo
        mongo_result = collection.delete_one({"message_id": mid})
        if mongo_result.deleted_count == 1:
            print(f"MongoDB: Deleted {mid}.")
            successfully_purged.append(mid)
        else:
            print(f"MongoDB: Could NOT delete {mid} (not found?).")
            failed_upstream.append(mid)
    else:
        print(f"Skipped MongoDB delete for {mid} (failed upstream).")
        failed_upstream.append(mid)
    # You may want a slight pause to avoid hammering DBs
    time.sleep(0.05)

# --- LOGGING ---
with open(AUDIT_LOG, "a") as f:
    for mid in successfully_purged:
        f.write(f"{mid}\n")
with open(FAILED_LOG, "a") as f:
    for mid in failed_upstream:
        f.write(f"{mid}\n")

print("\n--- PURGE SUMMARY ---")
print(f"Purged everywhere: {len(successfully_purged)}")
print(f"Failed/skipped (see {FAILED_LOG}): {len(failed_upstream)}")
print(f"Audit log written to {AUDIT_LOG}")

if failed_upstream:
    print("Some messages remain in Mongo because they could not be fully purged upstream. Check logs for details.")
