import os
import requests
from elevenlabs import stream, VoiceSettings
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

# Load ElevenLabs API credentials
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
TTS_VOICE_ID = os.getenv("TTS_VOICE_ID")


client = ElevenLabs(
    api_key=os.getenv("ELEVEN_API_KEY")
)

HEADERS = {
    "xi-api-key": ELEVEN_API_KEY,
    "Content-Type": "application/json"
}

def stream_speech(text):
    response = client.text_to_speech.convert_as_stream(
        text=text,
        voice_id=TTS_VOICE_ID,
        model_id="eleven_flash_v2_5",
        voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75, speed=1.1)
    )

    for chunk in response:
        if isinstance(chunk, bytes):
            yield chunk