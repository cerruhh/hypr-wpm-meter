import json
import os
import signal
import sys
from json import load
import pystray
import PIL.Image
from logging import info as loginfo

global typometer
window_name: str = "Typeometer"
filejf = open(file="config/general.json", mode="r")
settings:dict = load(filejf)
filejf.close()


def exit_func(icon, item):
    print("Exit!")
    os.kill(os.getpid(), signal.SIGTERM)


class Tray:
    @staticmethod
    def on_clicked(item):
        print(f"str_item: {str(item)}")
        print("Clicked Main!")
        if str(item) == "reforce positioning hypr":
            print("debug: force position")
            typometer.ipc.position_window()
        elif str(item) == "forc-move-pos-pixel-hypr":
            print("debug: forc-move-pos-pixel-hypr")
            typometer.ipc.send_command(f"dispatch movewindowpixel 1080 1080,title:^{window_name}$")

    def force_move(self, icon, item):
        print("force-mov")
        self.TypoMeter.ipc.send_command(f"dispatch movewindowpixel 900 0,title:^{window_name}$")

    def pos_com_force(self):
        print("self-force")

        direction = settings["general"]["window_position"]
        # payload_command = self.TypoMeter.get_hypr_command_from_list(com=direction)
        print(f"payload command: {payload_command}")
        payload_command = f"dispatch movewindowpixel 0 100%-100,title:^{window_name}$"

        print(self.TypoMeter.ipc.send_command(command=payload_command))

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
                pystray.MenuItem("force set positioning", self.pos_com_force),
                pystray.MenuItem("move-test", self.force_move)
            ))
        ))

        # Run the icon
        # self.trayicon.run()
        loginfo("Run started!")

# if __name__ == "__main__":
#     input("Test mode enabled. This is not meant to be run on its on, press enter to continue, exit to stop. ")
#     tray_class = Tray(None)
