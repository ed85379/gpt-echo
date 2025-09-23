from fastapi import APIRouter, Request
from collections import defaultdict
from bson import ObjectId
from app.core.memory_core import cortex, manager
from app.core.utils import serialize_doc

router = APIRouter(prefix="/api/memory", tags=["memory"])



@router.get("/")
def get_memory_layers():
    entries = cortex.get_entries_by_type(type_name="layer")
    layers = []
    for entry in entries:
        entry = serialize_doc(dict(entry))
        layers.append(entry)
    return layers

@router.post("/{doc_id}")
async def add_memory_entry(doc_id: str, request: Request):
    entry = await request.json()
    new_entry = manager.add_entry(doc_id, entry)
    return {"status": "ok", "entry": new_entry}

@router.patch("/{doc_id}/{entry_id}")
async def edit_memory_entry(doc_id: str, entry_id: str, request: Request):
    fields = await request.json()
    updated = manager.edit_entry(doc_id, entry_id, fields)
    if not updated:
        return {"status": "not found"}
    return {"status": "ok", "entry": updated}


@router.delete("/{doc_id}/{entry_id}")
async def delete_memory_entry(doc_id: str, entry_id: str):
    success = manager.delete_entry(doc_id, entry_id)
    if not success:
        return {"status": "not found"}
    return {"status": "ok", "deleted_id": entry_id, "doc_id": doc_id}