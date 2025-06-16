from fastapi import APIRouter, HTTPException, Body
from app.core.memory_core import log_message, log_message_test

router = APIRouter(prefix="/api/messages", tags=["messages"])

@router.post("/log")
async def log_message_endpoint(payload: dict = Body(...)):
    # Validate message fields if needed
    try:
        result = await log_message(**payload)
        return {"status": "ok", "message_id": result.get("message_id")}
    except Exception as e:
        import traceback
        print("Logging error in /api/messages/log:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

#@router.post("/api/messages/tag")
#async def tag_message_endpoint(payload: dict = Body(...)):
#    # This can match your existing logic
#    try:
#        result = await tag_message(**payload)
#        return {"status": "ok", "count": result.modified_count}
#    except Exception as e:
#        raise HTTPException(status_code=500, detail=str(e))