import os
import requests
from elevenlabs import stream, VoiceSettings
from elevenlabs.client import ElevenLabs
from app import config
from app.config import muse_config


# Load ElevenLabs API credentials
ELEVEN_API_KEY = config.ELEVEN_API_KEY
AUDIO_OUTPUT_PATH = config.AUDIO_OUTPUT_PATH

client = ElevenLabs(
    api_key=os.getenv("ELEVEN_API_KEY")
)

HEADERS = {
    "xi-api-key": ELEVEN_API_KEY,
    "Content-Type": "application/json"
}

def synthesize_speech(text: str, stability=0.5, similarity_boost=0.75) -> str:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{muse_config.get("VOICE_ID")}"

    payload = {
        "text": text,
        "model_id": "eleven_flash_v2_5",
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

async def stream_speech(text):
    response = client.text_to_speech.stream(
        text=text,
        voice_id=muse_config.get("TTS_VOICE_ID"),
        model_id="eleven_flash_v2_5",
        voice_settings=VoiceSettings(stability=0.6, similarity_boost=0.75, speed=1.0)
    )

    for chunk in response:
        if isinstance(chunk, bytes):
            yield chunk