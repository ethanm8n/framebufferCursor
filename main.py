"""Mouse cursor in the console.

Uses the linux framebuffer and mice driver to draw a mouse cursor on the screen.

Built on a Raspberry Pi 4 Model B (2018) running Raspbian GNU/Linux 10 (buster).

Tested with python 3.7.4.
"""
import sys
import fcntl
import struct
import os
import signal
import multiprocessing

FBIOGET_VSCREENINFO = 0x4600

class Painter(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.kill_event = multiprocessing.Event()

    def run(self):
        with open("/dev/fb0", "wb") as fb:
            # For screen information query the FBIOGET_VSCREENINFO ioctl.
            # Byte format taken from github.com/adafruit/Adafruit_CircuitPython_RGB_Display/blob/main/examples/rgb_display_fbcp.py
            var_screeninfo = struct.unpack("8I12I16I4I", fcntl.ioctl(fb, FBIOGET_VSCREENINFO, " " * ((8 + 12 + 16 + 4) * 4)))

            screen_width = var_screeninfo[0]
            screen_height = var_screeninfo[1]
            position_x = 0
            position_y = 0
            previous_position = -1

            with open("/dev/input/mice", "rb") as f:
                while not self.kill_event.is_set():
                    # Remove previous pixel.
                    if previous_position != -1:
                        fb.seek(previous_position, os.SEEK_SET)
                        fb.write(b"\x00\x00\x00\x00");

                    # Unpack 3 byte mouse file containing coordinates x and y.
                    d = struct.unpack("3b", f.read(3))
                    position_to_set_x = position_x + d[1]
                    position_to_set_y = position_y + d[2] * -1

                    # Pixels consist of 4 bytes and are painted left to right, line by line.
                    position = (position_to_set_y * screen_width + position_to_set_x) * 4

                    # Don't draw beyond limits of framebuffer.
                    if position < 0 or position > (screen_height * screen_width * 2):
                        continue

                    position_x = position_to_set_x
                    position_y = position_to_set_y

                    fb.seek(position, os.SEEK_SET)
                    fb.write(b"\xFF\xFF\xFF\xFF");

                    previous_position = position

class ProcessExit(Exception):
    pass

def onTerminate(signum, frame):
    raise ProcessExit

def main():
    signal.signal(signal.SIGTERM, onTerminate)
    signal.signal(signal.SIGINT, onTerminate)

    try:
        painter = Painter()
        painter.start()
        painter.join()
    except ProcessExit:
        print("Terminating process")
        painter.kill_event.set()

if __name__ == "__main__":
    main()
