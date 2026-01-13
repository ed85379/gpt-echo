from fastapi import APIRouter, HTTPException, Body
from typing import Any
from app.config import muse_config
from app.core.time_location_utils import reload_user_location

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
        # If any location-related fields changed, refresh the cache:
        if key == "USER_ZIPCODE" or key == "USER_TIMEZONE" or key == "USER_COUNTRYCODE":
            reload_user_location()
            print(f"CONFIG DEBUG: reloaded")
        return {"status": "ok", "key": key, "value": value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{key}/revert")
def revert_config_value(key: str):
    result = muse_config.live.delete_one({"_id": key})
    if result.deleted_count:
        # If any location-related fields changed, refresh the cache:
        if key == "USER_ZIPCODE" or key == "USER_TIMEZONE" or key == "USER_COUNTRYCODE":
            reload_user_location()
        return {"status": "reverted", "key": key}
    else:
        return {"status": "not_found", "key": key}



