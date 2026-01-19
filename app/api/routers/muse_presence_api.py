from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from app.services.tts_core import synthesize_speech, stream_speech
from collections import defaultdict
from app.core.muse_profile import muse_profile

profile_router = APIRouter(prefix="/api/muse_profile", tags=["muse_profile"])

@profile_router.get("/")
async def get_muse_profile():
    sections = muse_profile.all_sections()
    grouped = defaultdict(list)
    for section in sections:
        typ = section.get("section")
        # Convert ObjectId to str and remove or replace _id
        section = dict(section)  # Ensure it’s a dict
        if "_id" in section:
            section["_id"] = str(section["_id"])
        grouped[typ].append(section)
    return grouped

tts_router = APIRouter(prefix="/api/tts", tags=["tts"])

@tts_router.post("/")
async def tts(request: Request):
    data = await request.json()
    text = data.get("text", "")
    if not text:
        return JSONResponse(status_code=400, content={"error": "No text provided"})

    try:
        path = synthesize_speech(text)
        return FileResponse(path, media_type="audio/mpeg")
    except Exception as e:
        print("TTS error:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

@tts_router.post("/stream")
async def stream_tts(request: Request):
    data = await request.json()
    text = data.get("text", "")
    if not text:
        return JSONResponse({"error": "Missing 'text' in request body"}, status_code=400)

    async def audio_stream():
        async for chunk in stream_speech(text):
            yield chunk

    return StreamingResponse(audio_stream(), media_type="audio/mpeg")