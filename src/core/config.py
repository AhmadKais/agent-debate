import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "config.json"
_DEFAULT_RATE_LIMITS_PATH = Path(__file__).parent.parent.parent / "config" / "rate_limits.json"


def load_config(config_path: str | None = None) -> dict:
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    with open(path) as f:
        return json.load(f)


def load_rate_limits(config_path: str | None = None) -> dict:
    """Load rate limits config; returns {} if file is missing."""
    path = Path(config_path) if config_path else _DEFAULT_RATE_LIMITS_PATH
    try:
        with open(path) as f:
            return json.load(f)
    except OSError:
        return {}


def get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise OSError("ANTHROPIC_API_KEY not set in .env")
    return key
