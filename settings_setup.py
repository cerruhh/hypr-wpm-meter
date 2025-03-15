import os
import json

from evdev import InputDevice


def setup_config():
    if os.path.exists("config") and os.path.exists("config/general.json"):
        print("config already exists!")
        return

    keyboard_device = input("What is your keyboard device? (eg. /dev/input/event1) ")
    keyboard_input_device = InputDevice(keyboard_device)
    print("Success!")

    color_settings = False
    while True:
        color_ask = input("Do you want the color of the text to change, depending on your speed? (y/N) ")
        if color_ask.lower() == "y":
            print("setting true...")
            color_settings = True
            break
        elif color_ask.lower() == "n":
            print("settings false...")
            break

    directory_name: str = "config"
    try:
        os.mkdir(directory_name)
        print(f"Directory '{directory_name}' created successfully.")
    except FileExistsError:
        print(f"Directory '{directory_name}' already exists.")
    except PermissionError:
        print(f"Permission denied: Unable to create '{directory_name}'.")
    except Exception as e:
        print(f"An error occurred: {e}")

    json_d = {
        "general": {
            "color_switcher": color_settings,
            "input_device_path": keyboard_device
        }
    }

    with open(file="config/general.json", mode="w") as json_file:
        json.dump(json_d, json_file, indent=1)

    print("Setup done! settings file at config/general.json")
    return


if __name__ == "__main__":
    if input("warn: this file is not meant to be run! are you sure you want to continue? (y/N) ").lower() == "N":
        exit(1)

    setup_config()