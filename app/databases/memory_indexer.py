
import re
import os
from datetime import datetime, timezone
import hashlib
import pymongo
from sentence_transformers import SentenceTransformer
from app.config import muse_config
from app.core import utils, memory_core
from app.databases import qdrant_connector, graphdb_connector

MONGO_URI = muse_config.get("MONGO_URI")
MONGO_DBNAME = muse_config.get("MONGO_DBNAME")
MONGO_CONVERSATION_COLLECTION = muse_config.get("MONGO_CONVERSATION_COLLECTION")
CORTEX_DB = "muse_memory"
CORTEX_COLLECTION = "muse_cortex"

def assign_message_id(msg, filename=None, index=None):
    # Convert timestamp to ISO string if it's a datetime
    ts = msg.get("timestamp", "")
    if hasattr(ts, "isoformat"):
        ts = ts.isoformat()
    base = str(ts)
    base += "|" + msg.get("role", "")
    base += "|" + msg.get("source", "")
    base += "|" + msg.get("message", "")
    if filename:
        base += "|" + filename
    if index is not None:
        base += "|" + str(index)
    return hashlib.sha256(base.encode()).hexdigest()



def build_index(dryrun=False, message_id=None):
    """
    Indexes messages from Mongo to Qdrant and GraphDB.
    - If message_id is given, only update that message.
    - If not, updates all messages that are new or changed.
    """
    client = pymongo.MongoClient(MONGO_URI)
    coll = client[MONGO_DBNAME][MONGO_CONVERSATION_COLLECTION]
    mg = graphdb_connector.get_graphdb_connector().mg

    # Build the query
    if message_id:
        mongo_query = {"message_id": message_id}
    else:
        mongo_query = {
            "$or": [
                {"indexed_on": {"$exists": 0}},
                {
                    "$expr": {
                        "$gt": ["$updated_on", "$indexed_on"]
                    }
                }
            ]
        }

    total = 0
    updated_qdrant = 0
    updated_graphdb = 0

    print(f"Starting indexing... (message_id={message_id or 'ALL/NEW'})")
    for doc in coll.find(mongo_query):
        msg_id = doc.get("message_id")
        if not msg_id:
            print(f"Skipping message without message_id: {doc.get('_id')}")
            continue

        # ---- Qdrant update ----
        qdrant_entry = dict(doc)
        if not dryrun:
            text = qdrant_entry["message"]  # Get the message text
            vector = SentenceTransformer(muse_config.get("SENTENCE_TRANSFORMER_MODEL")).encode([text])[0]  # Generate the embedding vector
            qdrant_connector.upsert_single(qdrant_entry, vector)  # Upsert to Qdrant
        updated_qdrant += 1

        # ---- GraphDB update ----
        graphdb_success = True
        if not dryrun:
            try:
                graphdb_connector.create_message_and_user(mg, doc)
            except Exception as e:
                print(f"[GraphDB ERROR] message_id={msg_id} - {e}")
                graphdb_success = False
        updated_graphdb += 1 if graphdb_success else 0

        # ---- Mark as indexed ----
        if not dryrun:
            coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {"indexed_on": datetime.now(timezone.utc)}}
            )
        total += 1

    utils.write_system_log(level="debug", module="databases", component="graphdb", function="build_index", action="index_complete",
                     processed=total, qdrant_indexed=updated_qdrant, graphd_indexed=updated_graphdb, dryrun=dryrun, message_id=message_id)

    print(f"Indexing complete. Processed {total}. Qdrant updated: {updated_qdrant}. GraphDB updated: {updated_graphdb}.")

