import json

from src.core.paths import CONFIG_PATH

DEFAULTS = {
    "blender_path": r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    "game_path": r"D:\SteamLibrary\steamapps\common\Disney Infinity 3.0 Gold Edition",
    "mod_name": "mario",
}


def load_settings() -> dict:
    settings = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            settings.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return settings


def save_settings(settings: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(settings, indent=4), encoding="utf-8")
