import threading
import board
import neopixel
import time

# Configuration
LED_COUNT = 24           # Number of LEDs on your ring
LED_PIN = board.D18      # GPIO pin connected to the ring (PWM-capable)
BRIGHTNESS = 0.05         # 0.0 to 1.0

# Global pixel object
pixels = neopixel.NeoPixel(
    LED_PIN,
    LED_COUNT,
    brightness=BRIGHTNESS,
    auto_write=False
)
pulse_thread = None
_pulsing = False

def start_pulsing(color=(128, 0, 255), speed=0.03):
    global pulse_thread, _pulsing

    def pulse_loop():
        global _pulsing
        while _pulsing:
            for b in range(0, 256, 8):
                pixels.fill((int(color[0] * b / 255),
                             int(color[1] * b / 255),
                             int(color[2] * b / 255)))
                pixels.show()
                time.sleep(speed)
            for b in range(255, -1, -8):
                pixels.fill((int(color[0] * b / 255),
                             int(color[1] * b / 255),
                             int(color[2] * b / 255)))
                pixels.show()
                time.sleep(speed)

    if not _pulsing:
        _pulsing = True
        pulse_thread = threading.Thread(target=pulse_loop)
        pulse_thread.start()

def stop_pulsing():
    global _pulsing
    _pulsing = False
    time.sleep(0.1)
    off()

def off():
    pixels.fill((0, 0, 0))
    pixels.show()