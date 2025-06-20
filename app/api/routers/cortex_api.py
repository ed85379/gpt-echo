from fastapi import APIRouter, Request
from collections import defaultdict
from app.core.memory_core import cortex

router = APIRouter(prefix="/api/cortex", tags=["cortex"])

@router.get("/")
def get_cortex():
    entries = cortex.get_all_entries()
    grouped = defaultdict(list)
    for entry in entries:
        typ = entry.get("type")
        if typ == "encryption_key":
            continue
        # Convert ObjectId to str and remove or replace _id
        entry = dict(entry)  # Ensure it’s a dict
        if "_id" in entry:
            entry["_id"] = str(entry["_id"])
        grouped[typ].append(entry)
    return grouped

@router.put("/edit/{entry_id}")
async def edit_cortex_entry(entry_id: str, request: Request):
    data = await request.json()
    success = cortex.edit_entry(entry_id, data)
    return {"status": "ok" if success else "not found"}

@router.delete("/delete/{entry_id}")
async def delete_cortex_entry(entry_id: str):
    success = cortex.delete_entry(entry_id)
    return {"status": "ok" if success else "not found"}