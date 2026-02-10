from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from datetime import datetime, timezone
import json, uuid
from app.databases.mongo_connector import mongo_system
from app.core.memory_core import do_import

router = APIRouter(prefix="/api/import", tags=["import"])

@router.post("/upload")
async def upload_import(file: UploadFile = File(...)):
    collection_name = f"import_{uuid.uuid4().hex[:10]}"
    temp_coll = mongo_system.db[collection_name]
    imported = 0
    malformed = 0
    batch = []
    batch_size = 1000

    for line in file.file:
        try:
            record = json.loads(line)
            batch.append(record)
            if len(batch) >= batch_size:
                temp_coll.insert_many(batch)
                imported += len(batch)
                batch = []
        except Exception as e:
            malformed += 1

    if batch:
        temp_coll.insert_many(batch)
        imported += len(batch)

    # Record in import_history collection
    mongo_system.db.import_history.insert_one({
        "collection": collection_name,
        "filename": file.filename,
        "total": imported + malformed,
        "imported": imported,
        "malformed": malformed,
        "created_on": datetime.now(timezone.utc),
        "status": "pending"
    })

    return {"success": True, "collection": collection_name, "imported": imported, "malformed": malformed}

@router.get("/list")
def list_imports():
    entries = list(
        mongo_system.db.import_history.find(
            {"deleted": {"$ne": "true"}},  # Only show not-deleted
            {"_id": 0}
        ).sort("created_on", -1)  # Sort by newest first
    )
    return {"imports": entries}

from fastapi import Query

@router.delete("/delete")
def delete_import(collection: str = Query(...)):
    # Drop the temp import collection
    mongo_system.db[collection].drop()
    # Update import_history if pending
    import_history = mongo_system.db.import_history
    entry = import_history.find_one({"collection": collection})
    import_history.update_one(
        {"collection": collection},
        {"$set": {"deleted": "true"}}
    )
    return {"success": True}



@router.post("/process")
def process_import(collection: str = Query(...), background_tasks: BackgroundTasks = None):
    # Mark as processing
    mongo_system.db.import_history.update_one(
        {"collection": collection},
        {"$set": {"processing": True, "status": "pending"}}
    )
    background_tasks.add_task(do_import, collection)
    return {"success": True, "started": True}


@router.get("/progress")
def import_progress(collection: str = Query(...)):
    temp_coll = mongo_system.db[collection]
    total = temp_coll.count_documents({})
    done = temp_coll.count_documents({"imported": True})
    return {"done": done, "total": total}
