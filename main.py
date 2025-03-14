import sys
import logging
from collections import deque
from datetime import datetime, timedelta
import keyboard
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QGuiApplication
from PyQt5.QtWidgets import (QApplication, QLabel, QMainWindow, QWidget,
                             QVBoxLayout, QGraphicsDropShadowEffect)


class TypingSpeedMonitor(QMainWindow):
    key_pressed_signal = pyqtSignal(object)
    key_released_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.keystrokes = deque(maxlen=1000)
        self.pressed_keys = set()
        self.wpm_window = 5
        self.init_ui()
        self.setup_keyboard_listener()

        # Connect signals to thread-safe handlers
        self.key_pressed_signal.connect(self.handle_key_press_main)
        self.key_released_signal.connect(self.handle_key_release_main)

    def init_ui(self):
        # Same UI setup as before
        self.setWindowTitle("Typeometer")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 100)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 0, 10, 0)

        self.wpm_label = QLabel("WPM: 0")
        self.wpm_label.setFont(QFont("Arial", 30))
        self.wpm_label.setStyleSheet("color: white; margin: 0; padding: 0;")
        self.wpm_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(3, 3)
        self.wpm_label.setGraphicsEffect(shadow)

        layout.addWidget(self.wpm_label)
        self.setCentralWidget(container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_wpm)
        self.timer.start(200)

    def setup_keyboard_listener(self):
        # Emit signals from keyboard callbacks
        keyboard.on_press(lambda e: self.key_pressed_signal.emit(e))
        keyboard.on_release(lambda e: self.key_released_signal.emit(e))

    def handle_key_press_main(self, event):
        modifiers = {
            'shift', 'ctrl', 'alt', 'right shift', 'alt gr',
            'caps lock', 'tab', 'enter', 'esc', 'backspace',
            'delete', 'left', 'right', 'up', 'down', 'home',
            'end', 'page up', 'page down'
        }

        if event.name in modifiers:
            return

        valid_special_keys = {
            'space', 'comma', 'period', 'slash', 'backslash',
            'semicolon', 'apostrophe', 'minus', 'equal', 'grave',
            'bracketleft', 'bracketright', '1', '2', '3', '4', '5',
            '6', '7', '8', '9', '0'
        }

        valid_key = (
            event.name in valid_special_keys or
            (len(event.name) == 1 and event.name.isprintable())
        )

        if valid_key and event.name not in self.pressed_keys:
            self.pressed_keys.add(event.name)
            self.keystrokes.append(datetime.now())

    def handle_key_release_main(self, event):
        if event.name in self.pressed_keys:
            self.pressed_keys.remove(event.name)

    def calculate_wpm(self):
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.wpm_window)

        # Remove old keystrokes
        while self.keystrokes and self.keystrokes[0] < cutoff:
            self.keystrokes.popleft()

        if not self.keystrokes:
            return 0

        # Calculate WPM using rolling window
        elapsed_time = (now - self.keystrokes[0]).total_seconds()
        if elapsed_time == 0:
            return 0  # Prevent division by zero

        wpm = (len(self.keystrokes) / 5) * (60 / elapsed_time)
        return int(min(wpm, 500))  # Cap WPM for extreme cases

    def update_wpm(self):
        self.wpm_label.setText(f"WPM: {self.calculate_wpm()}")

    def position_window(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = 0
        y = screen.height() - self.height()

        if QGuiApplication.platformName() == "wayland":
            try:
                import subprocess
                subprocess.run([
                    "hyprctl",
                    "dispatch",
                    "movewindowpixel",
                    "0 100%-100",
                    f"title:Typeometer"
                ], check=True)
            except Exception as e:
                logging.error(f"Positioning failed: {e}")
        else:
            self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        self.position_window()

    def closeEvent(self, event):
        keyboard.unhook_all()
        super().closeEvent(event)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)

    window = TypingSpeedMonitor()
    window.show()

    # Required Hyprland rules
    hypr_rules = """\n
windowrulev2 = float,title:Typeometer
windowrulev2 = move 0 100%-100,title:Typeometer
windowrulev2 = size 400 100,title:Typeometer
windowrulev2 = noborder,title:Typeometer
windowrulev2 = noblur,title:Typeometer
windowrulev2 = focus,title:Typeometer\n
    """
    logging.info(f"Add to config:\n{hypr_rules}")

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        logging.info("Exiting...")
    finally:
        keyboard.unhook_all()
