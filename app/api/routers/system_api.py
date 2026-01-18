from fastapi import APIRouter, HTTPException, Body, Request
from typing import Any
from app.config import muse_config
from app.databases.mongo_connector import mongo_system, mongo
from app.core.time_location_utils import reload_user_location
from app.core.utils import serialize_doc
from app.core.states_core import set_states

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
    projection = {"pollstates": 0}

    state_doc = mongo_system.find_one_document(
        "muse_states",
        query=filter_query,
        projection=projection,
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


@states_router.patch("/{project_id}")
async def set_project_states(project_id: str, request: Request):
    data = await request.json()
    success = set_states(project_id, data)
    return {"status": "ok" if success else "not found"}

# UI Polling
uipolling_router = APIRouter(prefix="/api/uipolling", tags=["uipolling"])

@uipolling_router.get("/")
def get_ui_polling_state():
    # 1) states: anything under pollstates
    states = mongo_system.find_one_document(
        "muse_states",
        {"type": "states"},
        projection={"pollstates": 1, "_id": 0},
    ) or {}

    pollstates = states.get("pollstates", {}) or {}

    # 2) muse_profile: any section with pollable: true
    profile_docs = mongo.find_documents(
        "muse_profile",
        {"pollable": True},
        projection={"section": 1, "content": 1, "_id": 0},
    )

    # 3) config: any setting with pollable: true
    config_docs = muse_config.as_dict(pollable_only=True)

    return {
        "states": {
            "pollstates": pollstates
        },
        "muse_profile": profile_docs,
        "config": config_docs,
    }



