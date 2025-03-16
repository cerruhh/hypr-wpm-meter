import json
import os
import signal
import sys
from json import load
import pystray
import PIL.Image
from logging import info as loginfo

from PIL.ImageChops import screen

global typometer
window_name: str = "Typeometer"

filejf = open(file="config/general.json", mode="r")
settings: dict = load(filejf)
filejf.close()


def exit_func(icon, item):
    print("Exit!")
    os.kill(os.getpid(), signal.SIGTERM)


class Tray:
    @staticmethod
    def on_clicked(item):
        print(f"str_item: {str(item)}")
        print("Clicked Main!")

    def move_call_item(self):
        screen_item = self.TypoMeter.screen().availableGeometry()
        x_pos = screen_item.left()
        y_pos = screen_item.top()

        self.TypoMeter.move(x_pos, y_pos)
        self.TypoMeter.updateGeometry()
        print("Attempted move call to corner via debug: completed")
        print("Success not gua")

    def __init__(self, Typometer):
        self.TypoMeter = Typometer
        self.trayimage = PIL.Image.open("Assets/trayicon.png")
        self.trayicon = pystray.Icon("Typometer", self.trayimage, menu=pystray.Menu(
            pystray.MenuItem("Positions", pystray.Menu(
                pystray.MenuItem("Top-Left", self.on_clicked),
                pystray.MenuItem("Top-Right", self.on_clicked),
                pystray.MenuItem("Bottom-Right", self.on_clicked),
                pystray.MenuItem("Bottom-Left", self.on_clicked)
            )),
            pystray.MenuItem("Exit", action=exit_func),
            pystray.MenuItem("Debug", pystray.Menu(
                pystray.MenuItem("Move window to corner via move call", self.move_call_item)
            ))
        ))

        # Run the icon
        # self.trayicon.run()
        loginfo("Run started!")

# if __name__ == "__main__":
#     input("Test mode enabled. This is not meant to be run on its on, press enter to continue, exit to stop. ")
#     tray_class = Tray(None)
