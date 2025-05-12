import board
import neopixel
import time

pixels = neopixel.NeoPixel(board.D18, 24, brightness=0.5, auto_write=False)

def pulse_during_audio(color=(128, 0, 255), speed=0.05):
    # Simple pulsing loop — you can adjust this
    for i in range(0, 256, 5):
        pixels.fill((int(color[0] * i/255), int(color[1] * i/255), int(color[2] * i/255)))
        pixels.show()
        time.sleep(speed)
    for i in range(255, -1, -5):
        pixels.fill((int(color[0] * i/255), int(color[1] * i/255), int(color[2] * i/255)))
        pixels.show()
        time.sleep(speed)

def glow(color=(0, 50, 100)):
    pixels.fill(color)
    pixels.show()

def off():
    pixels.fill((0, 0, 0))
    pixels.show()