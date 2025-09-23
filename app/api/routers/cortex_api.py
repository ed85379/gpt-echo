from fastapi import APIRouter, Request
from collections import defaultdict
from bson import ObjectId
from app.core.memory_core import cortex
from app.core.utils import serialize_doc

router = APIRouter(prefix="/api/cortex", tags=["cortex"])



@router.get("/")
def get_cortex():
    entries = cortex.get_all_entries()
    grouped = defaultdict(list)
    for entry in entries:
        typ = entry.get("type")
        if typ == "encryption_key":
            continue
        # Serialize the entire entry to handle ObjectIds anywhere
        entry = serialize_doc(dict(entry))  # Ensure it’s a dict, then serialize
        grouped[typ].append(entry)
    return grouped

@router.get("/query")
def query_cortex(
    type: str = None,
    project_id: str = None,
    tags: str = None,
    is_deleted: bool = False
):
    query = {}
    if type:
        query["type"] = type
    if project_id:
        pid = ObjectId(project_id)
        query["$or"] = [
            {"project_id": pid},
            {"project_ids": pid}
        ]
    if tags:
        tag_list = tags.split(",")
        query["tags"] = {"$in": tag_list}
    if not is_deleted:
        query["is_deleted"] = {"$ne": True}

    entries = cortex.collection.find(query)
    result = [serialize_doc(e) for e in entries]
    return result

@router.patch("/{entry_id}")
async def edit_cortex_entry(entry_id: str, request: Request):
    data = await request.json()
    success = cortex.edit_entry(entry_id, data)
    return {"status": "ok" if success else "not found"}

@router.delete("/{entry_id}")
async def delete_cortex_entry(entry_id: str):
    success = cortex.delete_entry(entry_id)
    return {"status": "ok" if success else "not found"}