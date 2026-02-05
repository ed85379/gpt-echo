# /app/core/threads_core.py

from app.core.utils import generate_new_id
from app.core.time_location_utils import get_local_human_time
from datetime import datetime
from app.databases.mongo_connector import (
    mongo,
)


MONGO_THREADS_COLLECTION = "muse_threads"

def get_threads():
    mongo.ensure_mongo_collection(collection_name=MONGO_THREADS_COLLECTION)
    query = {}
    projection = {"_id": 0}
    threads = mongo.find_documents(
        collection_name=MONGO_THREADS_COLLECTION,
        query=query,
        projection=projection
    )
    results = []
    for thread in threads:
        mapped = {
            "thread_id": thread.get("thread_id"),
            "title": thread.get("title") or "",
            "is_hidden": thread.get("is_hidden", False),
            "is_private": thread.get("is_private", False),
            "is_archived": thread.get("is_archived", False),
        }
        results.append(mapped)
    return results


def create_thread(thread_id=None, title=None):
    mongo.ensure_mongo_collection(collection_name=MONGO_THREADS_COLLECTION)
    now = datetime.utcnow()
    if thread_id is None:
        thread_id = generate_new_id()
    default_title = f"Thread - {get_local_human_time(time_format='thread')}"
    thread = {
        "thread_id": thread_id,
        "title": title or default_title,
        "is_hidden": False,
        "is_private": False,
        "is_archived": False,
        "created_at": now,
        "updated_at": now
    }
    try:
        mongo.insert_one_document(MONGO_THREADS_COLLECTION, thread)
        # Return the stored representation (you can strip _id in the API if needed)
        return thread
    except Exception as e:
        print(f"Error creating thread: {e}")
        # Let the caller decide how to surface this
        raise

def edit_thread_fields(filter_query, patch_fields):
    thread = mongo.find_one_document(collection_name=MONGO_THREADS_COLLECTION, query=filter_query)
    if not thread:
        raise ValueError("Thread not found")
    updates = {}
    # Validate and set title
    if "title" in patch_fields:
        raw_title = patch_fields["title"]
        if raw_title is None:
            raise ValueError("Title cannot be null.")
        title = str(raw_title).strip()
        if not title:
            raise ValueError("Title must be at least 1 non-space character.")
        updates["title"] = title[:40]
    if "tags" in patch_fields:
        tags = patch_fields["tags"]
        # Only keep non-empty, trimmed strings, limit length of each tag and total number
        cleaned_tags = [str(t)[:24].strip() for t in tags if str(t).strip()]
        updates["tags"] = cleaned_tags[:10]  # e.g., max 10 tags of max 24 chars each
    if "is_hidden" in patch_fields:
        is_hidden = patch_fields["is_hidden"]
        updates["is_hidden"] = is_hidden
    if "is_private" in patch_fields:
        is_private = patch_fields["is_private"]
        updates["is_private"] = is_private
    if "is_archived" in patch_fields:
        is_archived = patch_fields["is_archived"]
        updates["is_archived"] = is_archived
    if updates:
        updates["updated_at"] = datetime.utcnow()
    if not updates:
        raise ValueError("No valid fields to update.")

    updated = mongo.update_one_document(
        collection_name=MONGO_THREADS_COLLECTION,
        filter_query=filter_query,
        update_data=updates
    )
    if updated and "thread_id" in updated:
        updated["thread_id"] = updated["thread_id"]
    return updated


