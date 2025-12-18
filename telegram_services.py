"""
Telegram services for linkkibot.
"""
from typing import Optional
import requests


def send_message(bot_token: str, chat_id: str, text: str, parse_mode: Optional[str] = "Markdown") -> bool:
	"""
	Send a message using Telegram Bot API.

	Returns True on success, False otherwise.
	"""
	if not bot_token or not chat_id:
		raise ValueError("bot_token and chat_id are required")

	url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
	payload = {
		"chat_id": chat_id,
		"text": text,
		"parse_mode": parse_mode,
	}

	try:
		resp = requests.post(url, json=payload, timeout=10)
		resp.raise_for_status()
		data = resp.json()
		return bool(data.get("ok"))
	except Exception:
		return False

