# app/core/files_core.py
import os
from fastapi import UploadFile

from bson import ObjectId
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from app.databases.mongo_connector import mongo
from app.config import muse_config, MONGO_MEMORY_COLLECTION, MONGO_FILES_COLLECTION, MONGO_CONVERSATION_COLLECTION, MONGO_PROJECTS_COLLECTION
from app.core.utils import chunk_file, ensure_list
from app.core.memory_core import log_message


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FILES_DIR = PROJECT_ROOT / "uploadedfiles"

def ensure_files_dir():
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR, exist_ok=True)

async def chunk_and_store_text(file, file_id, project_ids: Optional[List[str]]):
    chunks = chunk_file(file)
    message_ids = []
    for chunk in chunks:
        log_entry = {
            "role": "system",
            "message": chunk["content"],
            "source": "file",
            "metadata": {
                "filename": file.filename,
                "mimetype": file.content_type,
                "file_id": file_id,
                "file_index": chunk["index"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "start_byte": chunk["start_byte"],
                "end_byte": chunk["end_byte"]
            },
            "project_ids": project_ids  # May be empty
        }
        result = await log_message(**log_entry)
        msg_id = result.get("message_id")
        message_ids.append(msg_id)
    return message_ids


async def handle_text_file_upload(project_ids: Optional[List[str]], file: UploadFile):
    ensure_files_dir()
    file_bytes = await file.read()
    if not file_bytes:
        raise ValueError("No file data received.")

    new_file_id = ObjectId()
    file_path = os.path.join(FILES_DIR, str(new_file_id))
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Prepare project ObjectIds list (may be empty)
    project_obj_ids = [ObjectId(pid) for pid in project_ids] if project_ids else []

    # Chunk the file and log each chunk as a message
    chunks = chunk_file(file_bytes)
    message_ids = []
    for chunk in chunks:
        log_entry = {
            "role": "system",
            "message": chunk["content"],
            "source": "file",
            "metadata": {
                "filename": file.filename,
                "mimetype": file.content_type,
                "file_id": new_file_id,
                "file_index": chunk["index"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "start_byte": chunk["start_byte"],
                "end_byte": chunk["end_byte"]
            },
            "project_ids": project_obj_ids  # May be empty
        }
        result = await log_message(**log_entry)
        msg_id = result.get("message_id")
        message_ids.append(msg_id)

    file_doc = {
        "_id": new_file_id,
        "filename": file.filename,
        "mimetype": file.content_type,
        "size": len(file_bytes),
        "path": file_path,
        "message_ids": message_ids,
        "project_ids": project_obj_ids,
        "uploaded_on": datetime.utcnow(),
    }
    mongo.insert_one_document(MONGO_FILES_COLLECTION, file_doc)

    # For each project, add file_id to its file_ids array
    for pid in project_obj_ids:
        mongo.update_one_document_array(
            MONGO_PROJECTS_COLLECTION,
            {"_id": pid},
            {"$push": {"file_ids": new_file_id}}
        )

    return {
        "message": f"File '{file.filename}' uploaded and chunked.",
        "num_chunks": len(chunks),
        "message_ids": [str(mid) for mid in message_ids],
        "file_id": str(new_file_id),
        "path": file_path
    }

async def handle_image_file_upload(project_ids: Optional[List[str]], file: UploadFile):
    ensure_files_dir()
    file_bytes = await file.read()
    if not file_bytes:
        raise ValueError("No file data received.")

    new_file_id = ObjectId()
    new_fact_id = ObjectId()
    filename = file.filename
    mimetype = file.content_type
    _, ext = os.path.splitext(filename)
    file_path = os.path.join(FILES_DIR, str(new_file_id) + ext)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    project_obj_ids = [ObjectId(pid) for pid in project_ids] if project_ids else []



    # --- Auto-caption step ---
    from app.services.openai_client import get_openai_image_caption_bytes
    caption = get_openai_image_caption_bytes(
        file_bytes,
        #prompt="Describe this image in one clear, informative sentence for a project file caption.",
        prompt="Describe this image with a clear, detailed paragraph that would allow an LLM to understand the contents.",
        mime_type=mimetype or "image/jpeg"
    )

    file_doc = {
        "_id": new_file_id,
        "filename": filename,
        "mimetype": mimetype,
        "size": len(file_bytes),
        "path": file_path,
        "project_ids": project_obj_ids,
        "fact_id": new_fact_id,
        "uploaded_on": datetime.utcnow(),
        "caption": caption,
    }
    mongo.insert_one_document(MONGO_FILES_COLLECTION, file_doc)

    cortex_doc = {
        "_id": new_fact_id,
        "type": "fact",
        "file_id": new_file_id,
        "project_ids": project_obj_ids,
        "filename": filename,
        "text": caption,
        "mimetype": mimetype,
        "created_at": datetime.utcnow(),
    }
    mongo.insert_one_document(MONGO_MEMORY_COLLECTION, cortex_doc)

    # Link file to all specified projects
    for pid in project_obj_ids:
        mongo.update_one_document_array(
            MONGO_PROJECTS_COLLECTION,
            {"_id": pid},
            {"$push": {"file_ids": new_file_id}}
        )

    return {
        "message": f"Image '{filename}' uploaded and captioned.",
        "file_id": str(new_file_id),
        "caption": caption,
        "path": file_path
    }

async def modify_file_project_link_core(
    project_id: str,
    file_id: str,
    action: str,  # "attach" or "detach"
    *,
    mongo,
    index_queue
):
    # Choose mongo operator
    op = "$addToSet" if action == "attach" else "$pull"

    # 1. Project ⇄ File
    mongo.update_one_document_array(
        collection_name=MONGO_PROJECTS_COLLECTION,
        filter_query={"_id": ObjectId(project_id)},
        update_data={op: {"file_ids": ObjectId(file_id)}}
    )
    mongo.update_one_document_array(
        collection_name=MONGO_FILES_COLLECTION,
        filter_query={"_id": ObjectId(file_id)},
        update_data={op: {"project_ids": ObjectId(project_id)}}
    )

    # 2. Facts/Messages (recursive link)
    file_doc = mongo.find_one_document(MONGO_FILES_COLLECTION, {"_id": ObjectId(file_id)})
    for key in ("fact_id", "message_ids"):
        ids = file_doc.get(key)
        id_list = ensure_list(ids)
        for idx in id_list:
            if key == "fact_id":
                collection = MONGO_MEMORY_COLLECTION
                filter_query = {"_id": ObjectId(idx)}
            else:  # key == "message_ids"
                collection = MONGO_CONVERSATION_COLLECTION
                filter_query = {"message_id": idx}  # <-- Use message_id as primary key
            # Include your update fields here (with updated_on, etc)
            update_fields = {
                op: {"project_ids": ObjectId(project_id)},
                "$set": {"updated_on": datetime.utcnow()}
            }
            mongo.update_one_document_array(
                collection_name=collection,
                filter_query=filter_query,
                update_data=update_fields
            )
            # Re-index if message
            if collection == MONGO_CONVERSATION_COLLECTION:
                await index_queue.put(idx)

    return { "ok": True, "action": action, "indexing_queued": True }

def get_all_message_ids_for_files(file_ids):
    """
    Given a list of file_ids (ObjectIds), return a deduplicated list of all message_ids
    from those files. Skips files with missing or empty message_ids.
    """
    # Fetch all file docs in one go
    files = mongo.find_documents(
        collection_name=MONGO_FILES_COLLECTION,
        query={"_id": {"$in": file_ids}}
    )
    # Collect all message_ids, flatten, and dedupe
    all_message_ids = set()
    for file in files:
        mids = file.get("message_ids") or []
        all_message_ids.update(mids)
    return list(all_message_ids)