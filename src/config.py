"""
Configuration for linkkibot.

The values are read from the environment, which is filled from the .env file in the project root. 
Copy .env.example into .env and fill in the variables.
Variables that are already set in the environment, for example the ones Docker Compose injects take precedence over the .env file.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example into .env and fill in the variables."
        )
    return value


TELEGRAM_CHAT_ID = required("TELEGRAM_CHAT_ID")
EVENTS_URL = required("EVENTS_URL")
DATABASE_URL = required("DATABASE_URL")

SAMPLE_URL = os.environ.get("SAMPLE_URL", "")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
