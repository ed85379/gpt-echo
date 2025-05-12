import sounddevice as sd
import numpy as np
from openwakeword.model import Model
import queue
import time

wake_model = Model(wakeword_models=["hey_jarvis"])
q = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    q.put(indata.copy())

def listen_for_wakeword():
    print("🎧 Wake word listener running...")
    stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=16000, dtype="float32")
    with stream:
        while True:
            audio_chunk = q.get()
            result = wake_model.predict(audio_chunk)
            if result.get("hey_jarvis", 0) > 0.7:
                print("👂 Wake word detected!")
                return
            time.sleep(0.01)
