import os
import requests
from app import config

# Load ElevenLabs API credentials
ELEVEN_API_KEY = config.ELEVEN_API_KEY
TTS_VOICE_ID = config.get_setting("TTS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Default if not set
AUDIO_OUTPUT_PATH = config.PROJECT_ROOT / config.get_setting("VOICE_OUTPUT_DIR", "voice/") / "response.mp3"


HEADERS = {
    "xi-api-key": ELEVEN_API_KEY,
    "Content-Type": "application/json"
}

def synthesize_speech(text: str, stability=0.5, similarity_boost=0.75) -> str:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{TTS_VOICE_ID}"

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }

    response = requests.post(url, json=payload, headers=HEADERS)

    if response.status_code == 200:
        os.makedirs(os.path.dirname(AUDIO_OUTPUT_PATH), exist_ok=True)
        with open(AUDIO_OUTPUT_PATH, "wb") as f:
            f.write(response.content)
        return AUDIO_OUTPUT_PATH
    else:
        raise Exception(f"ElevenLabs TTS failed: {response.status_code} {response.text}")
