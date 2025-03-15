import sys
import pystray
import PIL.Image
from logging import info as loginfo

global typometer




def exit_func(icon, item):
    print("Exit!")
    quit(0)


class Tray:
    def on_clicked(icon, item):
        print("Clicked Main!")
        if str(item) == "reforce positioning hypr":
            typometer.ipc.position_window()

    def __init__(self, Typometer):
        self.TypoMeter = Typometer
        typometer = Typometer
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
                pystray.MenuItem("reforce positioning hypr", self.on_clicked)
            ))
        ))

        # Run the icon
        # self.trayicon.run()
        loginfo("Run started!")


# if __name__ == "__main__":
#     input("Test mode enabled. This is not meant to be run on its on, press enter to continue, exit to stop. ")
#     tray_class = Tray(None)
