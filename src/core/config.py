import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "config.json"


def load_config(config_path: str | None = None) -> dict:
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    with open(path) as f:
        return json.load(f)


def get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise OSError("ANTHROPIC_API_KEY not set in .env")
    return key
