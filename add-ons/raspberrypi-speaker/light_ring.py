import threading
import board
import neopixel
import time
import numpy as np

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
_active = False
spinner_thread = None

# For wake-word trigger
def fill_ring_one_by_one(color=(0, 0, 255), delay=0.02):
    for i in range(LED_COUNT):
        pixels[i] = color
        pixels.show()
        time.sleep(delay)
    time.sleep(0.2)  # hold briefly
    pixels.fill((0, 0, 0))
    pixels.show()

# For Echo thinking
def start_glow_loop(color=(128, 0, 255), speed=0.04, min_brightness=0.02, max_brightness=0.2):
    global _active, pulse_thread

    def glow_loop():
        global _active
        b_range = np.linspace(min_brightness, max_brightness, 32).tolist() + \
                  np.linspace(max_brightness, min_brightness, 32).tolist()
        while _active:
            for b in b_range:
                pixels.brightness = b
                pixels.fill(color)
                pixels.show()
                time.sleep(speed)

    if not _active:
        _active = True
        pulse_thread = threading.Thread(target=glow_loop)
        pulse_thread.start()



def start_pulsing(color=(128, 0, 255), speed=0.03):
    global pulse_thread, _active

    def pulse_loop():
        global _active
        while _active:
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

    if not _active:
        _active = True
        pulse_thread = threading.Thread(target=pulse_loop)
        pulse_thread.start()


# For Echo speaking
def start_spinner(color=(128, 0, 255), delay=0.06, trail_length=8, direction=1):
    global _active, spinner_thread

    def spinner_loop():
        global _active
        pixel_count = len(pixels)
        index = 0
        while _active:
            pixels.fill((0, 0, 0))  # Clear ring
            for i in range(trail_length):
                pos = (index - i * direction) % pixel_count
                fade = max(0, (1 - (i / trail_length))**1.8)
                faded_color = tuple(int(c * fade) for c in color)
                pixels[pos] = faded_color

            pixels.show()
            index = (index + direction) % pixel_count
            time.sleep(delay)

    if not _active:
        _active = True
        spinner_thread = threading.Thread(target=spinner_loop)
        spinner_thread.start()


def stop_spinner(fade=True, fade_steps=20, fade_delay=0.03):
    global _active
    _active = False
    time.sleep(0.1)  # Let thread settle

    if not fade:
        pixels.fill((0, 0, 0))
        pixels.show()
        return

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


def spin_comet(color=(128, 0, 255), delay=0.03, trail_length=5):
    for i in range(LED_COUNT + trail_length):
        for j in range(LED_COUNT):
            distance = i - j
            if 0 <= distance < trail_length:
                fade = max(0, 1 - distance / trail_length)
                pixels[j] = tuple(int(c * fade) for c in color)
            else:
                pixels[j] = (0, 0, 0)
        pixels.show()
        time.sleep(delay)

    # fade-out
    for _ in range(trail_length):
        for i in range(LED_COUNT):
            r, g, b = pixels[i]
            pixels[i] = (int(r * 0.6), int(g * 0.6), int(b * 0.6))
        pixels.show()
        time.sleep(0.05)

def _active():
    global _active
    _active = False
    time.sleep(0.1)
    off()

def off():
    pixels.fill((0, 0, 0))
    pixels.show()