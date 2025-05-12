import pvporcupine
import sounddevice as sd
import struct

def listen_for_wakeword():
    print("🎧 Wake word listener running (Porcupine, .ppn mode)...")

    # Use the raw .ppn file (no access key needed this way)
    porcupine = pvporcupine.create(
        keyword_paths=["./jarvis_raspberry-pi.ppn"]
    )

    def wake_callback():
        print("👂 Wake word detected!")
        from light_ring import spin_comet
        spin_comet(color=(128, 0, 255), delay=0.02)

    try:
        with sd.RawInputStream(
            samplerate=porcupine.sample_rate,
            channels=1,
            dtype='int16',
            blocksize=porcupine.frame_length
        ) as stream:
            while True:
                pcm = stream.read(porcupine.frame_length)[0]
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                if porcupine.process(pcm) >= 0:
                    wake_callback()
                    return
    finally:
        porcupine.delete()
