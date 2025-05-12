import asyncio
import websockets
import os
import json
from dotenv import load_dotenv
import light_ring
import subprocess
import tempfile
import requests

from tts_core import stream_speech
import simpleaudio as sa
from io import BytesIO
from pydub import AudioSegment

load_dotenv()

WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://10.1.1.137:5000/ws")  # Change IP as needed
API_URL = os.getenv("API_URL")
CLIENT_NAME = os.getenv("SPEAKER_NAME", "speaker")

def record_audio(duration=5, filename=None):
    """
    Records audio from the ATR4697-USB mic (card 4, device 0) using arecord.
    Duration in seconds. Returns path to WAV file or raw bytes if filename is None.
    """
    if filename is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        filename = tmp.name
        tmp.close()

    cmd = [
        "arecord",
        "-D", "plughw:4,0",
        "-f", "S16_LE",
        "-r", "48000",
        "-c", "1",
        "-t", "wav",
        "-d", str(duration),
        filename
    ]

    print(f"🎙️ Recording for {duration} seconds...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Recording failed: {e}")
        return None

    print(f"✅ Recording saved to {filename}")
    return filename

def send_audio_for_transcription(file_path):
    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(f"{API_URL}/transcribe", files=files)
            result = response.json()
            if "text" in result:
                return result["text"]
            else:
                print("❌ Transcription failed:", result)
                return None
    except Exception as e:
        print("❌ Error uploading audio:", e)
        return None

async def play_streaming_audio(audio_generator):
    buffer = BytesIO()
    try:
        light_ring.start_spinner()
        for chunk in audio_generator:
            buffer.write(chunk)
        buffer.seek(0)
        audio = AudioSegment.from_file(buffer, format="mp3")
        playback = sa.play_buffer(audio.raw_data, num_channels=audio.channels,
                                  bytes_per_sample=audio.sample_width, sample_rate=audio.frame_rate)
        playback.wait_done()
    except Exception as e:
        print(f"⚠️ Audio playback failed: {e}")
    finally:
        light_ring.stop_spinner()

async def handle_message(message):
    print(f"🔊 Echo says: {message}")
    audio_generator = stream_speech(message)
    await play_streaming_audio(audio_generator)

async def main():
    print(f"📡 Connecting to {WEBSOCKET_URL}...")
    async with websockets.connect(WEBSOCKET_URL) as ws:
        await ws.send(json.dumps({
            "listen_as": "speaker"
        }))

        print("✅ Speaker connected and listening for messages...")

        while True:
            try:
                message = await ws.recv()
                await handle_message(message)
            except websockets.ConnectionClosed:
                print("❌ Connection to server lost. Reconnecting...")
                await asyncio.sleep(5)
                await main()
            except Exception as e:
                print(f"⚠️ Error handling message: {e}")

if __name__ == "__main__":
    asyncio.run(main())
