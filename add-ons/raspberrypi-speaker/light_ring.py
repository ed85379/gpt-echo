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
spinner_thread = None

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



def start_spinner(color=(128, 0, 255), delay=0.06, trail_length=5):
    global _pulsing, spinner_thread

    def spinner_loop():
        global _pulsing
        pixel_count = len(pixels)
        index = 0
        while _pulsing:
            pixels.fill((0, 0, 0))  # Clear ring

            # Draw trail
            for i in range(trail_length):
                pos = (index - i) % pixel_count
                fade = max(0, (1 - (i / trail_length))**1.8)
                faded_color = tuple(int(c * fade) for c in color)
                pixels[pos] = faded_color

            pixels.show()
            index = (index + 1) % pixel_count
            time.sleep(delay)

    if not _pulsing:
        _pulsing = True
        spinner_thread = threading.Thread(target=spinner_loop)
        spinner_thread.start()

def stop_spinner(fade_steps=20, fade_delay=0.03):
    global _pulsing
    _pulsing = False
    time.sleep(0.1)  # Let thread settle

    # Smooth fade out
    for step in range(fade_steps, 0, -1):
        brightness = step / fade_steps
        for i in range(len(pixels)):
            r, g, b = pixels[i]
            pixels[i] = (int(r * brightness), int(g * brightness), int(b * brightness))
        pixels.show()
        time.sleep(fade_delay)

    pixels.fill((0, 0, 0))
    pixels.show()


def stop_pulsing():
    global _pulsing
    _pulsing = False
    time.sleep(0.1)
    off()

def off():
    pixels.fill((0, 0, 0))
    pixels.show()