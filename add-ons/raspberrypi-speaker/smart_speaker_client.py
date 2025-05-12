import asyncio
import websockets
import os
import json
from dotenv import load_dotenv
from light_ring import start_pulsing, stop_pulsing
from tts_core import stream_speech
import simpleaudio as sa
from io import BytesIO
from pydub import AudioSegment

load_dotenv()

WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://10.1.1.137:5000/ws")  # Change IP as needed
CLIENT_NAME = os.getenv("SPEAKER_NAME", "speaker")

async def play_streaming_audio(audio_generator):
    buffer = BytesIO()
    try:
        start_pulsing()
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
        stop_pulsing()

async def handle_message(message):
    print(f"🔊 Echo says: {message}")
    audio_generator = stream_speech(message)
    await play_streaming_audio(audio_generator)

async def main():
    print(f"📡 Connecting to {WEBSOCKET_URL}...")
    async with websockets.connect(WEBSOCKET_URL) as ws:
        await ws.send(json.dumps({
            "type": "register",
            "client": CLIENT_NAME,
            "role": "speaker"
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
