import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "config.json"


def load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return json.load(f)


def get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")
    return key
