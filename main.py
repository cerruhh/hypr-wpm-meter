import socket
import os
import sys
import logging
import time
import socket
import subprocess

from collections import deque
from datetime import datetime, timedelta
import threading
from evdev import InputDevice, categorize, ecodes, list_devices
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QProcess
from PyQt5.QtGui import QColor, QFont, QGuiApplication
from PyQt5.QtWidgets import (QApplication, QLabel, QMainWindow, QWidget,
                             QVBoxLayout, QGraphicsDropShadowEffect)
from pathlib import Path
import settings_setup
from json import load as json_load
import Classes.TrayIcon
import Classes.PopUps

settings_setup.setup_config()
global settings
with open(file="config/general.json", mode="r") as jfile:
    settings = json_load(jfile)


def get_color_from_wpm(wpm: int) -> str:
    # Check if color switcher is disabled.
    if not settings["general"]["color_switcher"]:
        return "white"

    if wpm < 120:
        return "white"
    elif 120 < wpm < 300:
        return "orange"
    else:
        return "red"


class TypingSpeedMonitor(QMainWindow):
    key_pressed_signal = pyqtSignal(object)
    key_released_signal = pyqtSignal(object)

    def __init__(self):
        self.window_width = 400  # Explicit width definition
        self.window_height = 100  # Explicit height definition

        super().__init__()
        self.setWindowTitle("Typeometer")
        self.init_ui()
        self.keystrokes = deque(maxlen=1000)
        self.pressed_keys = set()
        self.wpm_window = 5
        self.setup_keyboard_listener()
        self.Popups = Classes.PopUps.PopupWindow()

        self.key_pressed_signal.connect(self.handle_key_press_main)
        self.key_released_signal.connect(self.handle_key_release_main)

        self.trayicon = Classes.TrayIcon.Tray(self)
        threading.Thread(target=self.trayicon.trayicon.run).start()

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.NoDropShadowWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        if self.is_hyprland() and settings["general"].get("no_hyprland_nag", "0") == "0":
            self.Popups.hyprland_positions_not_supported()

    @staticmethod
    def is_hyprland():
        # Method 1: Check Hyprland-specific environment variable
        if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            return True

        # Method 2: Check XDG_CURRENT_DESKTOP
        xdg_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if "hyprland" in xdg_desktop:
            return True

        # Method 3: Check running processes (fallback)
        try:
            result = subprocess.run(
                ["pgrep", "-x", "Hyprland"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
        except FileNotFoundError:
            pass

        return False

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.NoDropShadowWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(400, 100)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 0, 10, 0)

        self.wpm_label = QLabel("WPM: 0")
        self.wpm_label.setFont(QFont("Arial", 30))
        self.wpm_label.setStyleSheet("color: white; margin: 0; padding: 0;")  # Base style
        # self.wpm_label.setFont(QFont("Arial", 30))
        # self.wpm_label.setStyleSheet("color: white; margin: 0; padding: 0;")
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
        devices = [InputDevice(path) for path in list_devices()]
        if settings["general"]["input_device_path"] != "":
            logging.info("keyboard device defined!")
            self.keyboard_dev = InputDevice("/dev/input/event3")
        else:
            # First try to find a device that looks like a keyboard
            for dev in devices:
                caps = dev.capabilities()
                # Check for keyboard keys and absence of mouse capabilities
                if ecodes.EV_KEY in caps:
                    # Exclude devices with relative axes (mice/trackpads)
                    if ecodes.EV_REL not in caps:
                        # Additional check for common keyboard identifiers
                        if any(k in dev.name.lower() for k in ['keyboard', 'kbd', 'keeb']):
                            self.keyboard_dev = dev
                            break

        # Fallback to first device with keys if no obvious keyboard found
        if not self.keyboard_dev:
            for dev in devices:
                if ecodes.EV_KEY in dev.capabilities():
                    self.keyboard_dev = dev
                    break

        if not self.keyboard_dev:
            logging.error("No keyboard device found!")
            return

        logging.info(f"Using keyboard device: {self.keyboard_dev.name}")

        # Rest of the method remains the same...
        self.keyboard_listener_thread = threading.Thread(
            target=self.read_keyboard_events, daemon=True)
        self.keyboard_listener_thread.start()

    def read_keyboard_events(self):
        try:
            for event in self.keyboard_dev.read_loop():
                if event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    if key_event.keystate == key_event.key_down:
                        self.key_pressed_signal.emit(key_event)
                    elif key_event.keystate == key_event.key_up:
                        self.key_released_signal.emit(key_event)
        except Exception as e:
            logging.error(f"Error reading keyboard events: {e}")

    def normalize_key_name(self, key_name):
        if key_name.startswith('KEY_'):
            key_name = key_name[4:]
        key_name = key_name.lower()
        modifier_mapping = {
            'leftshift': 'shift',
            'rightshift': 'shift',
            'leftctrl': 'ctrl',
            'rightctrl': 'ctrl',
            'leftalt': 'alt',
            'rightalt': 'alt',
            'altgr': 'alt gr',
            'capslock': 'caps lock',
            'pageup': 'page up',
            'pagedown': 'page down',
        }
        return modifier_mapping.get(key_name, key_name)

    def handle_key_press_main(self, key_event):
        key_name = self.normalize_key_name(key_event.keycode)

        modifiers = {
            'shift', 'ctrl', 'alt', 'alt gr', 'caps lock',
            'tab', 'enter', 'esc', 'backspace', 'delete',
            'left', 'right', 'up', 'down', 'home', 'end',
            'page up', 'page down'
        }

        if key_name in modifiers:
            return

        valid_special_keys = {
            'space', 'comma', 'period', 'slash', 'backslash',
            'semicolon', 'apostrophe', 'minus', 'equal', 'grave',
            'bracketleft', 'bracketright', '1', '2', '3', '4', '5',
            '6', '7', '8', '9', '0'
        }

        valid_key = (
                key_name in valid_special_keys or
                (len(key_name) == 1 and key_name.isprintable())
        )

        if valid_key and key_name not in self.pressed_keys:
            self.pressed_keys.add(key_name)
            self.keystrokes.append(datetime.now())

    def handle_key_release_main(self, key_event):
        key_name = self.normalize_key_name(key_event.keycode)
        if key_name in self.pressed_keys:
            self.pressed_keys.remove(key_name)

    def calculate_wpm(self):
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.wpm_window)

        while self.keystrokes and self.keystrokes[0] < cutoff:
            self.keystrokes.popleft()

        if not self.keystrokes:
            return 0

        elapsed_time = (now - self.keystrokes[0]).total_seconds()
        if elapsed_time == 0:
            return 0

        wpm = (len(self.keystrokes) / 5) * (60 / elapsed_time)
        return int(min(wpm, 500))

    def update_wpm(self):
        wpm = self.calculate_wpm()
        color = get_color_from_wpm(wpm=wpm)
        self.wpm_label.setText(f"WPM: {wpm}")
        self.wpm_label.setStyleSheet(f"color: {color}; margin: 0; padding: 0;")

    def position_window(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        position = settings["general"].get("window_position", "bottom-left")

        window_width = self.width()
        window_height = self.height()

        # Calculate positions for all corners
        positions = {
            "bottom-left": (0, screen.height() - window_height),
            "bottom-right": (screen.width() - window_width, screen.height() - window_height),
            "top-left": (0, 0),
            "top-right": (screen.width() - window_width, 0)
        }

        print(
            f"bl: {positions["bottom-left"]} br: {positions['bottom-left']} tl: {positions['top-left']} tr: {positions['top-right']}")

        x, y = positions.get(position, positions["bottom-left"])

        # Force window position through multiple methods
        self.move(x, y)
        self.setGeometry(x, y, self.width(), self.height())

        # Required for some Wayland compositors
        self.show()
        QTimer.singleShot(100, lambda: self.move(x, y))
        QTimer.singleShot(200, lambda: self.setGeometry(x, y, self.width(), self.height()))

    def showEvent(self, event):
        super().showEvent(event)

    def closeEvent(self, event):
        if hasattr(self, 'pos_timer'):
            self.pos_timer.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    # Add these before creating QApplication
    app = QApplication(sys.argv)
    window = TypingSpeedMonitor()
    window.show()
    app.exec_()

    logging.basicConfig(level=logging.INFO)
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        logging.info("Exiting...")
