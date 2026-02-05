# /app/api/routers/threads_api.py

from fastapi import APIRouter, HTTPException, status
from app.core import threads_core

router = APIRouter(prefix="/api/threads", tags=["threads"])

MONGO_THREADS_COLLECTION = "muse_threads"

@router.get("/")
def get_threads():
    threads = threads_core.get_threads()
    return {"threads": threads}

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_thread(body: dict):
    thread_id = body.get("thread_id")
    title = body.get("title")
    try:
        thread = threads_core.create_thread(thread_id=thread_id, title=title)
        # Strip any internal fields if needed
        thread_response = {
            "thread_id": thread.get("thread_id"),
            "title": thread.get("title", ""),
            "is_hidden": thread.get("is_hidden", False),
            "is_private": thread.get("is_private", False),
            "is_archived": thread.get("is_archived", False),
            "created_at": thread.get("created_at"),
            "updated_at": thread.get("updated_at"),
        }
        return {"thread": thread_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{key}")
def edit_thread(key: str, patch_fields: dict):
    try:
        print("PATCH fields received:", patch_fields)
        result = threads_core.edit_thread_fields({"thread_id": key}, patch_fields)
        return {"status": "ok", "key": key, "thread": result}
    except ValueError as e:
        # Bad input or not found
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")