from fastapi import APIRouter, HTTPException, Request
from app.databases.mongo_connector import mongo_system
from app.core.utils import serialize_doc
from app.core.states_core import set_states

router = APIRouter(prefix="/api/states", tags=["states"])

@router.get("/")
def get_ui_states():
    filter_query = {"type": "ui_states"}
    projection = {"pollstates": 0}

    state_doc = mongo_system.find_one_document(
        "muse_states",
        query=filter_query,
        projection=projection,
    )

    if not state_doc:
        # No doc yet → just return implicit defaults for the UI
        return {
            "type": "ui_states",
            "auto_assign": True,
            "blend_ratio": 0.5,
            "project_id": None,
        }

    state_doc = serialize_doc(state_doc)
    # Drop Mongo’s identity; keep only what the UI actually uses
    state_doc.pop("_id", None)
    return state_doc


@router.patch("/{project_id}")
async def set_ui_states(project_id: str, request: Request):
    data = await request.json()
    success = set_states(project_id, data)
    return {"status": "ok" if success else "not found"}
