import random
import asyncio
import time
import requests
from app import config
import feedparser
from urllib.parse import urljoin
from app.core.dispatch_message import dispatch_message
from app.core.memory_core import log_message, load_core_principles, load_profile
from app.core.discovery_core import load_discoveryfeeds_sources, load_echos_interests_sources
from app.core.openai_client import get_openai_response
from app.core.discord_client import start_discord_listener

THRESHOLD_API_URL = config.THRESHOLD_API_URL
ECHO_NAME = config.get_setting("system_settings.ECHO_NAME", "Assistant")
OPENAI_MODEL = config.get_setting("system_settings.OPENAI_MODEL", "gpt-4.1")


# --- New: Fetch Profile and Memory directly ---
def fetch_profile_and_memory():
    try:
        echo_profile = load_profile()
        core_principles = load_core_principles()
        return echo_profile, core_principles
    except Exception as e:
        print("Error loading profile and memory:", e)
        return "", ""

# --- Build the payload for WhisperGate ---
def build_whispergate_payload():
    """
    Gathers all current memory, discovery, and presence context to send to WhisperGate (GPT-3.5).
    Decides whether Echo should speak, reflect, or stay silent.
    """

    now = datetime.now(ZoneInfo(USER_TIMEZONE))

    # Phase 1: Check Cortex for active reminders
    timely_reminders = search_cortex_for_timely_reminders(now)

    if timely_reminders:
        context_source = "cortex"
        context_items = timely_reminders
    else:
        context_source = "discovery"
        context_items = {
            "time": get_local_time(),
            "weather": get_local_weather(),
            "discoveryfeeds": fetch_discoveryfeeds(),
            "echos_interests": fetch_echos_interests()
        }

    # Available action settings
    speak_endpoints = config.get_setting("SPEAK_ENDPOINTS", ["discord"])
    reflect_targets = config.get_setting("REFLECT_TARGETS", [])

    payload = {
        "profile": load_profile(),  # Echo's personality baseline
        "core_principles": load_core_principles(),  # Deep memory
        "context_source": context_source,
        "context_items": context_items,
        "available_speak_endpoints": speak_endpoints,
        "available_reflect_targets": reflect_targets,
        "current_time": now.isoformat()
    }

    return payload


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

            echo_profile, core_principles = fetch_profile_and_memory()

            # Build your full prompt
            full_prompt = f"{echo_profile}\n{core_principles}\n"

            # Later, this gets passed to OpenAI
            response = get_openai_response(full_prompt)

            await dispatch_message(response)
            log_message(role=ECHO_NAME, content=response)

        else:
            print("Decision: Silent this cycle.")

        await asyncio.sleep(3600)  # Sleep for 60 seconds before next heartbeat

# --- Combined Main ---
async def main():
    await asyncio.gather(
        run_echo_loop(),
        start_discord_listener()
    )

# --- Entrypoint ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("EchoLoop + Listener stopped.")
