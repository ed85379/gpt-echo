from pathlib import Path
import os
import json
from dotenv import load_dotenv

# Determine project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Secrets from .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PRIMARY_USER_DISCORD_ID = os.getenv("PRIMARY_USER_DISCORD_ID")
THRESHOLD_API_URL = os.getenv("THRESHOLD_API_URL", "http://localhost:8080")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

# Load static settings
CONFIG_PATH = PROJECT_ROOT / "threshold_config.json"

try:
    with open(CONFIG_PATH, "r") as f:
        _settings = json.load(f)
except Exception as e:
    print(f"Error loading threshold_config.json: {e}")
    _settings = {}

def get_setting(key, default=None):
    """
    Supports nested keys like "user_settings.USER_NAME".
    """
    keys = key.split(".")
    value = _settings
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value
