import random
import asyncio
import time
import requests
from app import config
from urllib.parse import urljoin
from dispatch_message import dispatch_message
from app.core.memory_core import log_message
from openai_client import get_openai_response

THRESHOLD_API_URL = config.THRESHOLD_API_URL
ECHO_NAME = config.get_setting("ECHO_NAME", "Assistant")
OPENAI_MODEL = config.get_setting("OPENAI_MODEL", "gpt-4-turbo")

# --- New: Fetch Profile and Memory from Local Flask Server ---
def fetch_profile_and_memory():
    try:
        profile_res = requests.post(THRESHOLD_API_URL, json={"prompt": "Who are you?"})
        root_res = requests.post(urljoin(THRESHOLD_API_URL, "/api/memoryroot"),
                                 json={"prompt": "What are your core principles?"})

        echo_profile = profile_res.json()["profile"]
        memory_root = root_res.json()["memory_root"]

        return echo_profile, memory_root

    except Exception as e:
        print("Error fetching profile and memory:", e)
        return "", ""

# --- WhisperGate Logic ---
def should_speak():
    # 30% chance to whisper on any cycle
    return random.random() < 0.3

# --- EchoLoop Logic ---
async def run_echo_loop():
    while True:
        print(f"Heartbeat: Checking if {ECHO_NAME} should whisper...")

        if should_speak():
            print("Decision: Whispering.")

            echo_profile, memory_root = fetch_profile_and_memory()

            # Build your full prompt
            full_prompt = f"{echo_profile}\n{memory_root}\n"

            # Later, this gets passed to OpenAI
            response = get_openai_response(full_prompt)

            await dispatch_message(response)
            log_message(role=ECHO_NAME, content=response)

        else:
            print("Decision: Silent this cycle.")

        await asyncio.sleep(10)  # Sleep for 60 seconds before next heartbeat

# --- Entrypoint ---
if __name__ == "__main__":
    try:
        asyncio.run(run_echo_loop())
    except KeyboardInterrupt:
        print("EchoLoop stopped.")
