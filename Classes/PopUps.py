from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox


class PopupWindow(QWidget):
    def __init__(self):
        super().__init__()

    @staticmethod
    def hyprland_positions_not_supported():
        msg = QMessageBox()
        msg.setWindowTitle("Hyprland cannot position window!")
        msg.setText("""Hyprland does not have the ability to move the meter on its own. please add these to your hyprland config for proper cornering (bottom left):
windowrulev2 = pin, title:Typeometer
windowrulev2 = float,title:Typeometer
windowrulev2 = move 0 100%-100,title:Typeometer
windowrulev2 = size 400 100,title:Typeometer
windowrulev2 = noborder,title:Typeometer
windowrulev2 = noblur,title:Typeometer
windowrulev2 = nofocus,title:Typeometer

Add "no_hyprland_nag": "1" to your general.json file to make this message dissapear.
""")
        ex_ = msg.exec_()


if __name__ == "__main__":
    input("Press enter to contiune, this file is not meant to be ran alone.")
    app = QApplication([])
    ex = PopupWindow()
    ex.show()
    app.exec_()
