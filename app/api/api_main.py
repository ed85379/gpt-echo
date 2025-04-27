from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
import os
import json
from app import config
from fastapi.middleware.cors import CORSMiddleware
from app.core.memory_core import (
    search_combined_memory,
    is_ingested,
    mark_ingested,
    log_message
)
from app.core.tts_core import synthesize_speech
from app.core.memory_core import load_profile, load_memory_root
from app.core.openai_client import get_openai_response
from app.core.memory_core import log_message

LOGS_DIR = config.PROJECT_ROOT / config.get_setting("LOGS_DIR", "logs/")
ECHO_NAME = config.get_setting("ECHO_NAME", "Echo")
USER_NAME = config.get_setting("USER_NAME", "User")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accept requests from any origin (you can restrict later if needed)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.post("/api/profile")
async def get_profile():
    profile_path = config.PROJECT_ROOT / "profiles" / "echo_profile.json"
    with open(profile_path, "r", encoding="utf-8") as f:
        profile_data = json.load(f)
    return {"profile": json.dumps(profile_data, indent=2)}

@app.post("/api/memoryroot")
async def get_memory_root():
    memory_root_path = config.PROJECT_ROOT / "profiles" / "memory_root.json"
    with open(memory_root_path, "r", encoding="utf-8") as f:
        memory_root_data = json.load(f)
    return {"memory_root": memory_root_data.get("root", "")}

## Future endpoint to dynamically pull summarized, compressed memory snippets from the ChatGPT API (or internal index), to build the active working memory window for Echo.
#@app.route("/api/context_snippets", methods=["POST"])
#def get_context_snippets():
#    prompt = request.json.get("prompt", "")
#    return jsonify({"snippets": SNIPPETS})

@app.post("/api/memory_snippets")
async def get_combined_memory_snippets(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    if not prompt:
        return {"snippets": []}
    results = search_combined_memory(prompt)
    return {"snippets": results}

@app.post("/api/tts")
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

@app.get("/api/logs")
def list_logs():
    files = [
        f for f in os.listdir(LOGS_DIR)
        if f.endswith(".jsonl") and f.startswith("echo-")
    ]
    logs = []
    for f in sorted(files, reverse=True):
        date_key = f.replace("echo-", "").replace(".jsonl", "")
        logs.append({
            "filename": f,
            "ingested": is_ingested(date_key)
        })
    return {"logs": logs}

@app.get("/api/logs/{filename}")
def get_log_preview(filename):
    path = os.path.join(LOGS_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "Not found"})

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    formatted = []
    for line in lines:
        try:
            msg = json.loads(line)
            role = msg.get("role", "unknown").capitalize()
            text = msg.get("message", "").strip()
            formatted.append(f"{role}: {text}")
        except:
            continue

    preview = "\n".join(formatted)
    return {"formatted": preview}

@app.post("/api/logs/mark/{filename}")
def mark_log_ingested(filename):
    if filename.startswith("echo-") and filename.endswith(".jsonl"):
        date_key = filename.replace("echo-", "").replace(".jsonl", "")
        mark_ingested(date_key)
        return {"status": "marked"}
    return JSONResponse(status_code=400, content={"error": "Invalid filename"})



@app.post("/api/talk")
async def talk_endpoint(request: Request):
    data = await request.json()
    user_input = data.get("prompt", "")
    if not user_input:
        return JSONResponse(status_code=400, content={"error": "No prompt provided."})

    # Load profile and memory
    profile_text = load_profile()
    memory_root = load_memory_root()

    # Pull relevant memory
    memory_snippets = search_combined_memory(user_input)

    # Build full context prompt
    full_prompt = profile_text.strip()

    if memory_root:
        full_prompt += "\n\n" + memory_root.strip()

    if memory_snippets:
        full_prompt += "\n\n" + "\n".join(memory_snippets)

    full_prompt += f"\n\n{config.get_setting('PRIMARY_USER_NAME', 'User')}: {user_input}\n{config.get_setting('ECHO_NAME', 'Assistant')}:"

    # Get Echo's response
    response = get_openai_response(full_prompt)

    # (Optional) Log the conversation
    log_message("user", user_input)
    log_message("echo", response)

    return {"response": response}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_main:app", host="0.0.0.0", port=5000, reload=True)
