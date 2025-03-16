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


class HyprlandIPC:
    def __init__(self):
        self.socket_path = self.find_hyprland_socket()
        self.max_retries = 5
        self.retry_count = 0

    def find_hyprland_socket(self):
        # Try different possible socket locations
        locations = [
            # Modern Hyprland location (0.30.0+)
            Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")) / "hypr",
            # Legacy location
            Path("/tmp") / "hypr",
            # Fallback location
            Path.home() / ".hypr"
        ]

        for base in locations:
            if base.exists():
                instances = list(base.glob("*"))
                if instances:
                    latest_instance = max(instances, key=lambda x: x.stat().st_mtime)
                    socket_path = latest_instance / ".socket.sock"
                    if socket_path.exists():
                        return str(socket_path)

        # Fallback to hyprctl if all else fails
        try:
            instances = subprocess.check_output(
                ["hyprctl", "instances", "-j"],
                text=True
            )
            instance_id = instances.strip().split("\n")[0].split(" ")[-1]
            return f"/run/user/{os.getuid()}/hypr/{instance_id}/.socket.sock"
        except Exception as e:
            raise RuntimeError(f"Hyprland socket not found: {e}")

    def send_command(self, command):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                sock.connect(self.socket_path)
                sock.sendall(command.encode() + b'\x00')
                return sock.recv(4096).decode().strip('\x00')
        except Exception as e:
            print(f"IPC Error: {e}")
            return None

    def position_window(self, window_title, pos_command: str) -> bool:
        print(pos_command)
        commands = [
            f"dispatch focuswindow title:^{window_title}$",
            f"dispatch togglefloating title:^{window_title}$",
            #pos_command,
            f"dispatch pin title:^{window_title}$",
            f"keyword windowrulevatime 0.1 float,title:^{window_title}$",
            f"keyword windowrulevatime 0.1 nofocus,title:^{window_title}$",
            f"keyword windowrulevatime 0.1 noborder,title:^{window_title}$"
        ]

        for cmd in commands:
            if not self.send_command(cmd):
                print("x")
                return False
        return True


class TypingSpeedMonitor(QMainWindow):
    key_pressed_signal = pyqtSignal(object)
    key_released_signal = pyqtSignal(object)

    def __init__(self):
        self.window_width = 400  # Explicit width definition
        self.window_height = 100  # Explicit height definition

        super().__init__()
        self.setWindowTitle("Typeometer")
        self.ipc = HyprlandIPC()
        self.init_ui()
        self.keystrokes = deque(maxlen=1000)
        self.pressed_keys = set()
        self.wpm_window = 5
        self.setup_keyboard_listener()

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
        QTimer.singleShot(500, self.force_positioning)

    def get_hypr_command_from_list(self, com: str) -> str:
        window_title = "Typeometer"
        print(com)
        if com.lower() == "bottom-right":
            print("bottom_right")
            return f"dispatch movewindowpixel 100%-{self.window_width + 10} 100%-{self.window_height + 10},title:^{window_title}$"
        elif com.lower() == "top-left":
            print("top_left")
            return f"dispatch movewindowpixel 10 10,title:^{window_title}$"
        elif com.lower() == "top-right":
            print("top_right")
            return f"dispatch movewindowpixel 100%-{self.window_width + 10} 10,title:^{window_title}$"
        elif com.lower() == "bottom-left":
            print("bottom_left")
            return f"dispatch movewindowpixel 0 100%-100,title:^{window_title}$"
        else:
            print("dispatch error, def")
            return f"dispatch movewindowpixel 0 100%-100,title:^{window_title}$"

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
        self.retry_positioning()

    def retry_positioning(self):
        com = self.get_hypr_command_from_list(settings["general"]["window_position"])
        if self.ipc.position_window("Typeometer", com):
            print("Window positioned successfully")
        elif self.ipc.retry_count < self.ipc.max_retries:
            print(f"Retrying positioning ({self.ipc.retry_count + 1}/{self.ipc.max_retries})")
            self.ipc.retry_count += 1
            QTimer.singleShot(300, self.retry_positioning)
        else:
            print("Failed to position window after multiple attempts")

    def force_positioning(self):
        com = self.get_hypr_command_from_list(settings["general"]["window_position"])
        if not self.ipc.position_window("Typeometer", com):
            print("Positioning failed, trying alternative methods...")
            self.fallback_positioning()

    def closeEvent(self, event):
        if hasattr(self, 'pos_timer'):
            self.pos_timer.stop()
        super().closeEvent(event)

    def fallback_positioning(self):
        """Fallback using XWayland properties"""
        self.move(0, self.screen().size().height() - self.height())
        self.setFixedSize(400, 100)
        # Keep trying until successful
        QTimer.singleShot(1000, self.force_positioning)


if __name__ == "__main__":
    # Add these before creating QApplication
    if "HYPRLAND_INSTANCE_SIGNATURE" not in os.environ:
        os.environ.update(
            subprocess.check_output("hyprctl env", shell=True, text=True).strip()
        )

    app = QApplication(sys.argv)
    window = TypingSpeedMonitor()
    window.show()
    app.exec_()

    logging.basicConfig(level=logging.INFO)

    hypr_rules = """\n
windowrulev2 = float,title:Typeometer
windowrulev2 = move 0 100%-100,title:Typeometer
windowrulev2 = size 400 100,title:Typeometer
windowrulev2 = noborder,title:Typeometer
windowrulev2 = noblur,title:Typeometer
windowrulev2 = pin,title:Typeometer
windowrulev2 = nofocus,title:Typeometer\n
    """
    logging.info(f"Add to config:\n{hypr_rules}")

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        logging.info("Exiting...")
