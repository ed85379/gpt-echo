import os
import requests
from elevenlabs import stream, VoiceSettings
from elevenlabs.client import ElevenLabs
from app.config import muse_settings, admin_config, AUDIO_OUTPUT_PATH


# Load ElevenLabs API credentials
ELEVEN_API_KEY = muse_settings.get_section("api_keys").get("TTS_API_KEY")

client = ElevenLabs(
    api_key=muse_settings.get_section("api_keys").get("TTS_API_KEY")
)

HEADERS = {
    "xi-api-key": ELEVEN_API_KEY,
    "Content-Type": "application/json"
}

def synthesize_speech(text: str, stability=0.5, similarity_boost=0.75) -> str:
    url = f"{admin_config.get_section('apis').get('TTS_API_URL')}{muse_settings.get_section('muse_config').get('TTS_VOICE_ID')}"

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
        voice_id=muse_settings.get_section('muse_config').get('TTS_VOICE_ID'),
        model_id="eleven_flash_v2_5",
        voice_settings=VoiceSettings(stability=0.6, similarity_boost=0.75, speed=1.0)
    )

    for chunk in response:
        if isinstance(chunk, bytes):
            yield chunk