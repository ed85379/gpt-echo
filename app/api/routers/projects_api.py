from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
import asyncio
from bson import ObjectId
from app.databases.mongo_connector import mongo
from app.config import muse_config
from app.core import projects_core

router = APIRouter(prefix="/api/projects", tags=["projects"])
MONGO_PROJECTS_COLLECTION = muse_config.get("MONGO_PROJECTS_COLLECTION")

@router.get("/")
def get_projects():
    query = {}
    projects = mongo.find_documents(
        collection_name=MONGO_PROJECTS_COLLECTION,
        query=query,
    )
    result = []
    for project in projects:
        mapped = {
            "_id": str(project["_id"]),
            "name": project.get("name") or "",
            "description": project.get("description") or "",
            "tags": project.get("tags", []),
            "notes": project.get("notes", []),
            "hidden": project.get("hidden", False),
        }
        result.append(mapped)

    return {"projects": result[::-1]}


@router.put("/{key}/visibility")
def toggle_project_visibility(key: str):
    try:
        result = projects_core.toggle_visibility({"_id": key})
        return {"status": "ok", "key": key, "hidden": result.hidden}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{key}")
def edit_project(key: str, patch_fields: dict):
    try:
        print("PATCH fields received:", patch_fields)
        result = projects_core.edit_project_fields({"_id": key}, patch_fields)
        return {"status": "ok", "key": key, "project": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{key}/tags")
def get_project_tags(key: str):
    from bson import ObjectId  # Ensure ObjectId is imported

    # Build the aggregation pipeline
    pipeline = [
        {"$match": {"project_id": ObjectId(key)}},
        {"$unwind": "$user_tags"},
        {"$group": {"_id": "$user_tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}}
    ]
    tag_docs = list(mongo.db.muse_conversations.aggregate(pipeline))
    return {"tags": [{"tag": doc["_id"], "count": doc["count"]} for doc in tag_docs]}