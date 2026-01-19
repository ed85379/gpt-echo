from fastapi import APIRouter, HTTPException, Body, Request
from typing import Any
from app.config import muse_config
from app.databases.mongo_connector import mongo_system, mongo
from app.core.time_location_utils import reload_user_location
from app.core.utils import serialize_doc
from app.core.states_core import set_states, extract_pollable_states

config_router = APIRouter(prefix="/api/config", tags=["config"])

@config_router.get("/")
def get_full_config():
    return muse_config.as_dict()

@config_router.get("/grouped")
def get_grouped_config():
    return muse_config.as_grouped(include_meta=True)


@config_router.put("/{key}")
def set_config_value(key: str, value: Any = Body(..., embed=True)):
    print(f"key: {key}, value: {value}")
    try:
        muse_config.set(key, value)
        # If any location-related fields changed, refresh the cache:
        if key == "USER_ZIPCODE" or key == "USER_TIMEZONE" or key == "USER_COUNTRYCODE":
            reload_user_location()
            print(f"CONFIG DEBUG: reloaded")
        return {"status": "ok", "key": key, "value": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.delete("/{key}/revert")
def revert_config_value(key: str):
    result = muse_config.live.delete_one({"_id": key})
    if result.deleted_count:
        # If any location-related fields changed, refresh the cache:
        if key == "USER_ZIPCODE" or key == "USER_TIMEZONE" or key == "USER_COUNTRYCODE":
            reload_user_location()
        return {"status": "reverted", "key": key}
    else:
        return {"status": "not_found", "key": key}

# States
states_router = APIRouter(prefix="/api/states", tags=["states"])

@states_router.get("/")
def get_states():
    filter_query = {"type": "states"}


    state_doc = mongo_system.find_one_document(
        "muse_states",
        query=filter_query,
        projection=None,
    )

    if not state_doc:
        # No doc yet → just return implicit defaults for the UI
        return {
            "type": "states",
            "auto_assign": True,
            "blend_ratio": 0.5,
            "project_id": None,
        }

    state_doc = serialize_doc(state_doc)
    # Drop Mongo’s identity; keep only what the UI actually uses
    state_doc.pop("_id", None)
    return state_doc

@states_router.get("/{project_id}")
def get_per_project_states(project_id: str):
    filter_query = {"type": "states"}
    projection = {"_id": 0, "projects.per_project": 1}

    per_projects_doc = mongo_system.find_one_document(
        "muse_states",
        query=filter_query,
        projection=projection
    )

    # No states doc or no projects/per_project yet → implicit defaults
    if not per_projects_doc:
        return {
            "auto_assign": True,
            "blend_ratio": 0.5
        }

    per_projects_doc = serialize_doc(per_projects_doc)

    # Walk safely down the nested structure
    projects = per_projects_doc.get("projects", {})
    per_project = projects.get("per_project", {})
    project_state = per_project.get(project_id, {})

    auto_assign = project_state.get("auto_assign", True)
    blend_ratio = project_state.get("blend_ratio", 0.5)

    return {
        "auto_assign": auto_assign,
        "blend_ratio": blend_ratio
    }

@states_router.patch("/{project_id}")
async def set_project_states(project_id: str, request: Request):
    data = await request.json()
    success = set_states(project_id, data)
    return {"status": "ok" if success else "not found"}

# UI Polling
uipolling_router = APIRouter(prefix="/api/uipolling", tags=["uipolling"])

@uipolling_router.get("/")
def get_ui_polling_state():
    # 1) states: anything with pollable: true
    states = extract_pollable_states()

    # 2) muse_profile: any section with pollable: true
    profile_docs = mongo.find_documents(
        "muse_profile",
        {"pollable": True},
        projection={"section": 1, "content": 1, "_id": 0},
    )

    # 3) config: any setting with pollable: true
    config_docs = muse_config.as_dict(pollable_only=True)

    return {
        "states": states,
        "muse_profile": profile_docs,
        "config": config_docs,
    }



