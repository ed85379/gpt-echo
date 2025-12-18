import os
from bson import ObjectId
from datetime import datetime
from pathlib import Path
from app.databases.mongo_connector import mongo
from app.config import muse_config


collection_name = muse_config.get("MONGO_PROJECTS_COLLECTION")
MONGO_PROJECTS_COLLECTION = muse_config.get("MONGO_PROJECTS_COLLECTION")
MONGO_FILES_COLLECTION = muse_config.get("MONGO_FILES_COLLECTION")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECTFILES_DIR = PROJECT_ROOT / "projectfiles"

def toggle_visibility(filter_query):
    # Assume filter_query is like {"_id": some_id} (string or ObjectId)

    # Convert string id to ObjectId if needed
    if "_id" in filter_query and not isinstance(filter_query["_id"], ObjectId):
        try:
            filter_query["_id"] = ObjectId(filter_query["_id"])
        except Exception:
            # Defensive: fallback to string if not a valid ObjectId
            pass

    project = mongo.find_one_document(collection_name, filter_query)
    if not project:
        raise ValueError("Project not found")

    new_hidden = not project.get("hidden", False)
    updated = mongo.update_one_document(
        collection_name,
        filter_query,
        {"hidden": new_hidden}
    )
    # Return a minimal result object for the API
    return type("ToggleResult", (), {"hidden": new_hidden, "project": updated})()

def toggle_archived(filter_query):
    # Assume filter_query is like {"_id": some_id} (string or ObjectId)

    # Convert string id to ObjectId if needed
    if "_id" in filter_query and not isinstance(filter_query["_id"], ObjectId):
        try:
            filter_query["_id"] = ObjectId(filter_query["_id"])
        except Exception:
            # Defensive: fallback to string if not a valid ObjectId
            pass

    project = mongo.find_one_document(collection_name, filter_query)
    if not project:
        raise ValueError("Project not found")

    new_archived = not project.get("archived", False)
    visibility = mongo.update_one_document(
        collection_name,
        filter_query,
        {"hidden": new_archived}
    )
    updated = mongo.update_one_document(
        collection_name,
        filter_query,
        {"archived": new_archived}
    )
    # Return a minimal result object for the API
    return type("ToggleResult", (), {"archived": new_archived, "project": updated})()

def edit_project_fields(filter_query, patch_fields):
    # Convert string id to ObjectId if needed
    if "_id" in filter_query and not isinstance(filter_query["_id"], ObjectId):
        try:
            filter_query["_id"] = ObjectId(filter_query["_id"])
        except Exception:
            pass

    project = mongo.find_one_document(collection_name, filter_query)
    if not project:
        raise ValueError("Project not found")


    updates = {}

    # Validate and set name
    if "name" in patch_fields:
        name = (patch_fields["name"] or "").strip()[:40]
        updates["name"] = name if name else "Untitled"
    # Validate and set description
    if "description" in patch_fields:
        desc = (patch_fields["description"] or "").strip()
        updates["description"] = desc[:1024]  # Example limit
    if "shortdesc" in patch_fields:
        desc = (patch_fields["shortdesc"] or "").strip()
        updates["shortdesc"] = desc[:80]  # Example limit
    # Validate and set notes
    if "notes" in patch_fields:
        notes = patch_fields["notes"]
        # Ensure notes is a list of non-empty, trimmed strings, limited in number and length
        cleaned_notes = [str(n)[:256].strip() for n in notes if str(n).strip()]
        updates["notes"] = cleaned_notes[:50]  # Example max 50 notes
    if "tags" in patch_fields:
        tags = patch_fields["tags"]
        # Only keep non-empty, trimmed strings, limit length of each tag and total number
        cleaned_tags = [str(t)[:24].strip() for t in tags if str(t).strip()]
        updates["tags"] = cleaned_tags[:10]  # e.g., max 10 tags of max 24 chars each
    if updates:
        updates["updated_at"] = datetime.utcnow()
    if not updates:
        raise ValueError("No valid fields to update.")

    updated = mongo.update_one_document(
        collection_name,
        filter_query,
        updates
    )
    if updated and "_id" in updated:
        updated["_id"] = str(updated["_id"])
    return updated

