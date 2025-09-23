import pymongo
import hashlib
from datetime import datetime, timezone
import time
from app import config
from app.services.openai_client import get_openai_autotags  # You may need to adjust the import

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "muse_memory"
COLLECTION = "muse_conversations"
OPENAI_MODEL = "gpt-4.1-mini"  # or whatever your nano model is

def standardize_timestamp(ts):
    if ts.endswith("Z"):
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    elif "+" in ts or "-" in ts[-6:]:
        dt = datetime.fromisoformat(ts)
    else:
        dt = datetime.fromisoformat(ts)
        dt = dt.astimezone(timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def assign_message_id(record):
    bits = [
        record.get('timestamp', ''),
        record.get('role', ''),
        record.get('source', ''),
        record.get('message', ''),
    ]
    to_hash = "|".join(str(b) for b in bits)
    return hashlib.sha256(to_hash.encode('utf-8')).hexdigest()

def get_autotags_via_openai(text):
    """Call OpenAI and extract tags (returns a list of tags)."""
    try:
        # This function should call OpenAI and parse the tags as a list.
        # You’ll need to implement get_openai_autotags in openai_client.py.
        return get_openai_autotags(text, model=OPENAI_MODEL)
    except Exception as e:
        print(f"Auto-tagging failed: {e}")
        return []

client = pymongo.MongoClient(MONGO_URI)
coll = client[DB_NAME][COLLECTION]

#total = coll.count_documents({})
total = coll.count_documents({ "auto_tags.1": { "$exists": False } })
#for idx, record in enumerate(coll.find({}), 1):
for idx, record in enumerate(coll.find({ "auto_tags.1": { "$exists": False } }), 1):

    updated = False

    # 1. Standardize timestamp
    try:
        std_ts = standardize_timestamp(record['timestamp'])
        if std_ts != record['timestamp']:
            record['timestamp'] = std_ts
            updated = True
    except Exception as e:
        print(f"Record {record['_id']}: timestamp parse error: {e}")

    # 2. Assign message_id if missing or different
    new_id = assign_message_id(record)
    if record.get('message_id') != new_id:
        record['message_id'] = new_id
        updated = True

    # 3. Add auto_tags if missing
    #if 'auto_tags' not in record:
    tags = get_autotags_via_openai(record.get('message', ''))
    record['auto_tags'] = tags
    record['updated_on'] = datetime.now(timezone.utc).isoformat()
    updated = True
    time.sleep(0.1)  # adjust this based on your rate limits

    # 4. Write back if changed
    if updated:
        #coll.update_one({'_id': record['_id']}, {"$set": record})
        coll.update_one({'_id': record['_id']}, {"$set": {"auto_tags": tags, "updated_on": record['updated_on']}})
    if idx % 100 == 0 or idx == total:
        print(f"{idx}/{total} records processed.")

print("Migration complete!")
