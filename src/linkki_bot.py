"""
Linkki Jyväskylä ry telegram bot.

Fetches events JSON from a configured URL and posts new events to Telegram.

Run:
  python3 linkki_bot.py [--dry-run] [--sample]
"""

import os
import sys
import datetime
import json
import argparse
import calendar
import re
from typing import Any, Dict, List

import requests

from telegram_services import send_message
from db_services import DB


TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
EVENTS_URL = os.environ["EVENTS_URL"]

def end_of_month(dt: datetime.datetime) -> datetime.datetime:
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    last_date = datetime.date(dt.year, dt.month, last_day)
    tz = dt.tzinfo
    return datetime.datetime.combine(last_date, datetime.time.max).replace(tzinfo=tz)

def end_of_week(dt: datetime.datetime, week_start: int = 0) -> datetime.datetime:
    # week_start: 0=Monday, 6=Sunday
    wd = dt.weekday()
    days_to_end = (week_start + 6 - wd) % 7
    last_date = (dt + datetime.timedelta(days=days_to_end)).date()
    tz = dt.tzinfo
    return datetime.datetime.combine(last_date, datetime.time.max).replace(tzinfo=tz)


def fetch_json(url: str) -> Any:
    """
    Fetch events json from api.
    """
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def clean_html(text: str) -> str:
    """
    Cleans HTML from text by extracting href URLs from <a> tags
    and removes other HTML tags aswell.
    
    Example: <a href="https://example.com">link text</a> -> https://example.com
    """
    text = re.sub(r'<br>', '\n', text)
    text = re.sub(r'<a\s+href="([^"]+)"[^>]*>.*?</a>', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def normalize_events(data: Any) -> List[Dict]:
    """
    Normalize data into a list of event dicts.

    Accepts either a list of events or a dict with `events` key.
    Currently not necessary, but perhaps in the future if the api is modified.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "events" in data and isinstance(data["events"], list):
            return data["events"]
        return [data]
    return []


def format_message(event: Dict) -> str:
    """
    Format a single event dict into a message string.

    Tries api event fields: summary, start_iso8601, description, url.
    """
    parts = []
    
    if title := event.get("summary"):
        parts.append(f"*{title}*")

    if start := event.get("start_iso8601"):
        dt = datetime.datetime.fromisoformat(start)
        parts.append(f"Päivämäärä: {dt.strftime("%d.%m.%y")}")
        if dt.hour != 0 or dt.minute != 0:
            parts.append(f"Alkaa: {dt.strftime("%H:%M")}")

    if location := event.get("location"):
        if isinstance(location, dict):
            location = f"[{location["string"]}]({location["url"]})"
        parts.append(f"Missä: {location}")

    if link := event.get("url"):
        parts.append(f"Linkki tapahtumaan: {link}")

    if description := event.get("description"):
        truncated = description if len(description) <= 400 else description[:400] + "..."
        clean = clean_html(truncated)
        parts.append(f"Mitä: \n{clean}")

    return "\n".join(parts) if parts else json.dumps(event)


def get_events_from_api() -> List[Dict]:
    """
    Gets events from linkki api and normalize them into List[Dict].
    """
    try:
        data = fetch_json(EVENTS_URL)
        print(data)
    except Exception as e:
        print(f"Failed to fetch events JSON from {EVENTS_URL}: {e}", file=sys.stderr)

    events = normalize_events(data)
    return events

def save_events_to_db(events: List[Dict]):
    """
    Save new events into database and skip old events or if there is no database.
    """
    new_events = []
    for event in events:
        try:
            if db.save_event_if_new(event):
                new_events.append(event)
            else:
                print("Skipping already saved event")
        except Exception as ex:
            print(f"Database error when saving event: {ex}", file=sys.stderr)
    return new_events

def poll_events():
    """
    Fetch events from the api handle them in db_services.py and post new events.
    """
    api_events = get_events_from_api()

    new_events = save_events_to_db(api_events)
    messages = []
    for ev in new_events:
        text = "Uusi tapahtuma!!\n"
        text += format_message(ev)
        text += "\n\n"
        messages.append(text)
    for message in messages:
        ok = send_message(TELEGRAM_CHAT_ID, message, parse_mode="Markdown")
        if not all(ok.values()):
            print("Failed to send message for event:", ev, file=sys.stderr)

    return 0

def post_events(modes: list[str] = ["month", "dry-run"]) -> int:
    """
    Run the core bot service once. Fetch events from the api and send them to chat specified in .env.
    """
    now = datetime.datetime.now()

    text = ""
    events = []
    if "day" in modes:
        text += "*Tänään:*\n\n"
        events = db.get_events_end(now, datetime.datetime(now.year, now.month, now.day, 23, 59, 59))
    elif "week" in modes:
        text += "*Tällä viikolla:*\n\n"
        events = db.get_events_end(now, end_of_week(now))
    elif "month" in modes:
        text += "*Tässä kuussa:*\n\n"
        events = db.get_events_end(now, end_of_month(now))

    for ev in events:
        text += format_message(ev)
        text += "\n\n"
    if len(events) < 1:
        text += "Ei tapahtumia :("
    
    sent = 0
    if "dry-run" in modes:
        print("DRY-RUN:\n", text)
    else:
        ok = send_message(TELEGRAM_CHAT_ID, text, parse_mode="Markdown")
        if not all(ok.values()):
            print("Failed to send message for event:", ev, file=sys.stderr)
        else:
            sent += 1

    print(f"Processed {len(events)} events, sent {sent} messages.")
    return 0


def main(argv=None):
    global db, EVENTS_URL
    parser = argparse.ArgumentParser(description="Simple JSON -> Telegram bot")
    parser.add_argument("--sample", action="store_true", help="Use sample JSON file")
    parser.add_argument("--modes", nargs='+', help="Bot running mode.", required=True)
    args = parser.parse_args(argv)

    modes = args.modes

    db = DB()
    db.ensure_tables()

    if args.sample:
        EVENTS_URL = os.environ["SAMPLE_URL"]

    if "post_events" in modes:
        poll_events()
        post_events(modes=modes)
    elif "poll_events" in modes:
        poll_events()


if __name__ == "__main__":
    sys.exit(main())
