
from bson import ObjectId
from datetime import datetime, timezone
from typing import Dict, Any
from app.databases.mongo_connector import mongo_system
from app.config import muse_config

def set_active_project(project_id: str):
    filter_query = {"type": "states"}

    state_doc = mongo_system.find_one_document(
        "muse_states",
        query=filter_query,
        projection=None,
    )

    # If doc doesn't exist, create it with exactly what we were given
    if not state_doc:
        new_doc = {
            "type": "states",
            "project_id": project_id,
            "global": { "auto_assign": True, "blend_ratio": 0.5 }
        }
        mongo_system.insert_one_document("muse_states", new_doc)

        return {
            "project_id": {
                "changed": True,
                "previous": None,
                "current": project_id,
            },
        }

    # Ensure fields exist even on legacy docs
    stored_project_id = state_doc.get("project_id", None)

    updates: Dict[str, Any] = {}
    changes: Dict[str, Dict[str, Any]] = {}

    # --- project_id ---
    if stored_project_id != project_id:
        updates["project_id"] = project_id
        changes["project_id"] = {
            "changed": True,
            "previous": stored_project_id,
            "current": project_id,
        }
    else:
        changes["project_id"] = {
            "changed": False,
            "previous": stored_project_id,
            "current": stored_project_id,
        }

    if updates:
        mongo_system.update_one_document(
            "muse_states",
            filter_query=filter_query,
            update_data=updates,
        )

    return changes


def set_states(project_id: str, updates: dict) -> bool:
    """
    Partially update states.per_project[project_id] with the given fields.

    Example:
      project_id = "68743eebc6c3ad0a405db259"
      updates = {"auto_assign": False, "blend_ratio": 0.7}
    """
    if not isinstance(updates, dict) or not updates:
        return False
    if not project_id:
        return False

    # Build the per_project.* keys
    per_project_prefix = f"per_project.{project_id}"
    set_fields = {
        f"{per_project_prefix}.{k}": v
        for k, v in updates.items()
    }

    # Just $set these fields; no $setOnInsert, no upsert
    result = mongo_system.update_one_document(
        "muse_states",
        {"type": "states"},
        set_fields,
    )

    # If no doc matched, result will be None
    return bool(result)

def set_motd(text: str):
    """
    Sets the MOTD message that appears in the UI
    """
    if not text:
        return False
    now = datetime.now(timezone.utc)
    result = mongo_system.update_one_document(
        "muse_states",
        {"type": "states"},
        {"pollstates.motd.text": text, "pollstates.motd.updated_on": now},
    )

    return bool(result)