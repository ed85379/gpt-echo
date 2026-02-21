from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional
from app.core.memory_core import cortex, manager
from app.core.utils import serialize_doc
from app.core.reminders_core import handle_snooze, handle_skip, handle_toggle

memory_router = APIRouter(prefix="/api/memory", tags=["memory"])

@memory_router.get("/")
def get_memory_layers():
    entries = cortex.get_entries_by_type(type_name="layer")
    layers = []
    for entry in entries:
        entry = serialize_doc(dict(entry))
        layers.append(entry)
    return layers

@memory_router.get("/{doc_id}")
def get_memory_layer(doc_id: str):
    # Decide type based on doc_id prefix
    if doc_id.startswith("project_facts_"):
        query = {"type": "project_layer", "id": doc_id}
    elif doc_id == "reminders":
        query = {"type": "reminder_layer", "id": doc_id}
    else:
        query = {"type": "layer", "id": doc_id}

    results = cortex.get_entries(query)

    if not results:
        raise HTTPException(status_code=404, detail="Layer not found")

    # Since IDs are unique, we expect at most one result
    layer = serialize_doc(dict(results[0]))
    return layer

@memory_router.post("/{doc_id}")
async def add_memory_entry(doc_id: str, request: Request):
    entry = await request.json()
    new_entry = manager.add_entry(doc_id, entry)
    return {"status": "ok", "entry": new_entry}

@memory_router.patch("/{doc_id}/{entry_id}")
async def edit_memory_entry(doc_id: str, entry_id: str, request: Request):
    fields = await request.json()
    updated = manager.edit_entry(doc_id, entry_id, fields)
    if not updated:
        return {"status": "not found"}
    return {"status": "ok", "entry": updated}


@memory_router.delete("/{doc_id}/{entry_id}")
async def delete_memory_entry(doc_id: str, entry_id: str):
    success = manager.delete_entry(doc_id, entry_id)
    if not success:
        return {"status": "not found"}
    return {"status": "ok", "deleted_id": entry_id, "doc_id": doc_id}

reminders_router = APIRouter(prefix="/api/reminders", tags=["reminders"])

class ReminderActionPayload(BaseModel):
    action: Literal["snooze", "skip", "toggle"]
    snooze_until: Optional[str] = None   # ISO 8601
    skip_until: Optional[str] = None     # ISO 8601
    status: Optional[Literal["enabled", "disabled"]] = None

@reminders_router.post("/{reminder_id}/action")
def reminder_action(reminder_id: str, payload: ReminderActionPayload):
    # sanity: make sure path id and payload id don’t drift
    base_payload = {"id": reminder_id}

    if payload.action == "snooze":
        if not payload.snooze_until:
            raise HTTPException(status_code=400, detail="snooze_until is required for snooze")
        return handle_snooze(
            {
                **base_payload,
                "snooze_until": payload.snooze_until,
            }
        )

    if payload.action == "skip":
        if not payload.skip_until:
            raise HTTPException(status_code=400, detail="skip_until is required for skip")
        return handle_skip(
            {
                **base_payload,
                "skip_until": payload.skip_until,
            }
        )

    if payload.action == "toggle":
        if not payload.status:
            raise HTTPException(status_code=400, detail="status is required for toggle")
        return handle_toggle(
            {
                **base_payload,
                "status": payload.status,
            }
        )

    raise HTTPException(status_code=400, detail="Unknown action")