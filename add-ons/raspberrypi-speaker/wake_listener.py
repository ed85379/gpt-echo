import pvporcupine
import sounddevice as sd
import numpy as np
import queue
import time
import scipy.signal
import os
from dotenv import load_dotenv

load_dotenv()

PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")

def downsample(data, from_rate, to_rate):
    return scipy.signal.resample_poly(data, up=to_rate, down=from_rate).astype(np.int16)

def listen_for_wakeword():
    print("🎧 Wake word listener running with 48kHz → 16kHz downsampling...")

    porcupine = pvporcupine.create(
        access_key=PICOVOICE_ACCESS_KEY,
        keyword_paths=["./hey_iris.ppn"],  # or use absolute path if needed
        sensitivities=[0.75]
    )

    audio_q = queue.Queue()
    INPUT_RATE = 48000
    TARGET_RATE = 16000
    DOWNSAMPLE_RATIO = INPUT_RATE // TARGET_RATE

    def callback(indata, frames, time_info, status):
        if status:
            print(status)
        audio_q.put(indata.copy())

    try:
        with sd.InputStream(
            samplerate=INPUT_RATE,
            channels=1,
            dtype='int16',
            blocksize=1024,
            callback=callback,
            device=1  # Replace with correct device index if needed
        ):
            buffer = np.array([], dtype=np.int16)
            print("🔁 Listening...")

            while True:
                chunk = audio_q.get().flatten()
                buffer = np.concatenate((buffer, chunk))

                while len(buffer) >= DOWNSAMPLE_RATIO * porcupine.frame_length:
                    segment = buffer[:DOWNSAMPLE_RATIO * porcupine.frame_length]
                    buffer = buffer[DOWNSAMPLE_RATIO * porcupine.frame_length:]

                    downsampled = downsample(segment, INPUT_RATE, TARGET_RATE)
                    if downsampled.size > 0:
                        try:
                            squared = np.square(downsampled.astype(np.float32))
                            mean_sq = np.mean(squared)
                            rms = np.sqrt(mean_sq) if mean_sq > 0 else 0
                        except Exception as e:
                            print(f"\n⚠️ RMS error: {e}")
                    else:
                        rms = 0

                    result = porcupine.process(downsampled)
                    if result >= 0:
                        print("\n👂 Wake word detected!")
                        from light_ring import spin_comet, start_spinner
                        spin_comet()
                        return
    finally:
        porcupine.delete()
