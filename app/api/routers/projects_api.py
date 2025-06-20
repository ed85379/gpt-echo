from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
import asyncio
from app.databases.mongo_connector import mongo
from app.config import muse_config

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
            "tags": project.get("tags", []),
            "notes": project.get("notes", []),
            "hidden": project.get("hidden", False),
        }
        result.append(mapped)

    return {"projects": result[::-1]}
