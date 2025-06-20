from fastapi import APIRouter, HTTPException, Body
from typing import Any
from app.config import muse_config

router = APIRouter(prefix="/api/config", tags=["config"])

@router.get("/")
def get_full_config():
    return muse_config.as_dict()

@router.get("/grouped")
def get_grouped_config():
    return muse_config.as_grouped(include_meta=True)


@router.put("/{key}")
def set_config_value(key: str, value: Any = Body(..., embed=True)):
    print(f"key: {key}, value: {value}")
    try:
        muse_config.set(key, value)
        return {"status": "ok", "key": key, "value": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{key}/revert")
def revert_config_value(key: str):
    result = muse_config.live.delete_one({"_id": key})
    if result.deleted_count:
        return {"status": "reverted", "key": key}
    else:
        return {"status": "not_found", "key": key}



