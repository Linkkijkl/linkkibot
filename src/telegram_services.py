"""
Telegram services for linkkibot.
"""
from typing import Optional
import os
import requests
from get_docker_secret import get_docker_secret

TELEGRAM_BOT_TOKEN = get_docker_secret("TELEGRAM_BOT_TOKEN")

def send_message(chat_ids: str | list[str], text: str, parse_mode: Optional[str] = "Markdown") -> dict[str, bool]:
    """
    Send a message using Telegram Bot API.

    Returns True on success, False otherwise.
    """
    if isinstance(chat_ids, str):
        chat_ids = [chat_ids]
    
    telegram_endpoint = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    results: dict[str, bool] = {}
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            resp = requests.post(telegram_endpoint, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            results[chat_id] = bool(data.get("ok"))
        except Exception:
            results[chat_id] = False
    return results
