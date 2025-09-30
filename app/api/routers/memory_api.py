from fastapi import APIRouter, Request, HTTPException
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

@router.get("/{doc_id}")
def get_memory_layer(doc_id: str):
    # Decide type based on doc_id prefix
    if doc_id.startswith("project_facts_"):
        query = {"type": "project_layer", "id": doc_id}
    else:
        query = {"type": "layer", "id": doc_id}

    results = cortex.get_entries(query)

    if not results:
        raise HTTPException(status_code=404, detail="Layer not found")

    # Since IDs are unique, we expect at most one result
    layer = serialize_doc(dict(results[0]))
    return layer

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