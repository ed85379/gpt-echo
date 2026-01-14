from fastapi import APIRouter
from app.databases.mongo_connector import mongo_system, mongo


router = APIRouter(prefix="/api/uipolling", tags=["uipolling"])

@router.get("/")
def get_ui_polling_state():
    # 1) ui_states: anything under pollstates
    ui_states = mongo_system.find_one_document(
        "muse_states",
        {"type": "ui_states"},
        projection={"pollstates": 1, "_id": 0},
    ) or {}

    pollstates = ui_states.get("pollstates", {}) or {}

    # 2) muse_profile: any section with pollable: true
    profile_docs = mongo.find_documents(
        "muse_profile",
        {"pollable": True},
        projection={"section": 1, "content": 1, "_id": 0},
    )

    # 3) config: any setting with pollable: true
    config_docs = mongo_system.find_documents(
        "muse_config",
        {"pollable": True},
        projection={"_id": 1, "value": 1,},
    )

    return {
        "ui_states": {
            "pollstates": pollstates
        },
        "muse_profile": profile_docs,
        "config": config_docs,
    }