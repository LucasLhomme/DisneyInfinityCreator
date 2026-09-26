import json
import os

CONFIG_PATH = "src/config/settings.json"

def load_settings():
    if not os.path.exists(CONFIG_PATH):
        return {"blender_path": r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(settings):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)
