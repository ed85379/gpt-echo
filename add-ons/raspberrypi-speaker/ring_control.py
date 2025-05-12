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

def glow(color=(0, 20, 255)):
    pixels.fill(color)
    pixels.show()

def pulse(color=(255, 20, 50), cycles=3, speed=0.03):
    for _ in range(cycles):
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

def off():
    pixels.fill((0, 0, 0))
    pixels.show()

def test():
    glow((0, 255, 0))
    time.sleep(1)
    pulse((255, 50, 0))
    off()

if __name__ == "__main__":
    test()
