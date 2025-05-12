import asyncio
import websockets
import json
from tts_core import stream_speech
from light_ring import pulse_during_audio  # You'll define this
from pydub import AudioSegment
import simpleaudio as sa
import io

def play_audio_chunk(chunk: bytes):
    try:
        if not chunk or len(chunk) < 1024:  # Skip small/empty chunks
            return

        audio = AudioSegment.from_file(io.BytesIO(chunk), format="mp3")
        raw_data = audio.raw_data

        play_obj = sa.play_buffer(
            raw_data,
            num_channels=audio.channels,
            bytes_per_sample=audio.sample_width,
            sample_rate=audio.frame_rate
        )

        play_obj.wait_done()

    except Exception as e:
        print(f"⚠️ Audio playback failed: {e}")


WS_SERVER_URL = "ws://10.1.1.137:5000/ws"  # Adjust as needed

from pydub import AudioSegment
import simpleaudio as sa
import io

# Accumulate chunks before decoding
buffer = io.BytesIO()

async def handle_speech(text):
    print(f"[Echo] Speaking: {text}")
    buffer.seek(0)
    buffer.truncate(0)

    async for chunk in stream_speech(text):
        buffer.write(chunk)

    try:
        buffer.seek(0)
        audio = AudioSegment.from_file(buffer, format="mp3")
        raw_data = audio.raw_data

        play_obj = sa.play_buffer(
            raw_data,
            num_channels=audio.channels,
            bytes_per_sample=audio.sample_width,
            sample_rate=audio.frame_rate
        )
        pulse_during_audio()  # Optional: while playing
        play_obj.wait_done()

    except Exception as e:
        print(f"⚠️ Buffered audio playback failed: {e}")

async def speaker_loop():
    async with websockets.connect(WS_SERVER_URL) as websocket:
        # Identify this client as a speaker
        await websocket.send(json.dumps({
            "listen_as": "speaker"
        }))

        print("[Smart Speaker] Connected and listening...")

        async for message in websocket:
            try:
                if message.startswith("{"):
                    payload = json.loads(message)
                    text = payload.get("text", "")
                else:
                    text = message.strip()

                if text:
                    await handle_speech(text)

            except Exception as e:
                print(f"⚠️ Error handling message: {e}")

async def main():
    while True:
        try:
            await speaker_loop()
        except Exception as e:
            print(f"⚠️ Disconnected or error: {e}")
            await asyncio.sleep(5)  # Reconnect delay

if __name__ == "__main__":
    asyncio.run(main())