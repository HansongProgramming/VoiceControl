import json

from app.config import CONFIG_PATH


def load_commands() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {item["trigger"]: item for item in data if "trigger" in item}
        return data
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def save_commands(commands: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(list(commands.values()), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
