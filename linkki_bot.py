"""
Linkki Jyväskylä ry telegram bot.

Fetches events JSON from a configured URL and posts new events to Telegram.

Run:
  python3 linkki_bot.py [--dry-run] [--sample]
"""
from __future__ import annotations

import os
import sys
import datetime
import json
import argparse
import calendar
from typing import Any, Dict, List, Optional

import requests

from telegram_services import send_message
from db_services import DB


bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")
events_url = os.environ.get("EVENTS_URL")
db = bool(os.environ.get("DATABASE_URL"))

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

def fetch_json(url: str, timeout: int = 10) -> Any:
    """
    Fetch events json from api.
    """
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


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


def form_message(event: Dict) -> str:
    """
    Format a single event dict into a message string.

    Tries api event fields: summary, start_iso8601, description, url.
    """
    parts = []
    title = event.get("summary")
    if title:
        parts.append(f"*{title}*")

    start = event.get("start_iso8601")
    if start:
        dt = datetime.datetime.fromisoformat(start)
        parts.append(f"Päivämäärä: {dt.strftime("%d.%m.%y")}")
        if dt.hour != 0 or dt.minute != 0:
            parts.append(f"Alkaa: {dt.strftime("%H:%M")}")

    location = event.get("location")
    if location:
        if type(location) == dict:
            location = f"[{location["string"]}]({location["url"]})"
        parts.append(f"Missä: {location}")

    #Not used. Maybe at some point we could have the link to the event on the website.
    link = event.get("url")
    if link:
        parts.append(f"Linkki tapahtumaan: {link}")

    desc = event.get("description")
    if desc:
        short = desc if len(desc) <= 400 else desc[:400] + "..."
        parts.append(f"Mitä: {short}")


    return "\n".join(parts) if parts else json.dumps(event)


def get_events_from_api() -> List[Dict]:
    """
    Gets events from linkki api and normalize them into List[Dict].
    """
    try:
        data = fetch_json(events_url)
        print(data)
    except Exception as e:
        print(f"Failed to fetch events JSON from {events_url}: {e}", file=sys.stderr)
        return 1

    events = normalize_events(data)
    if not events:
        print("No events found.")
        return 0
    return events

def save_events_to_db(events: List[Dict]):
    """
    Save new events into database and skip old events or if there is no database.
    """
    new_events = []
    for ev in events:
        is_new = True
        if db:
            try:
                is_new = db.save_event_if_new(ev)
                if is_new:
                    new_events.append(ev)
            except Exception as e:
                print(f"Database error when saving event: {e}", file=sys.stderr)
                continue

        if not is_new:
            print("Skipping already saved event")
            continue
    return new_events

def poll_events() -> int:
    """
    Fetch events from the api handle them in db_services.py and post new events.
    """
    if not events_url:
        print("Please set EVENTS_URL environment variables.", file=sys.stderr)
        return 2
    api_events = get_events_from_api()

    new_events = save_events_to_db(api_events)
    messages = []
    for ev in new_events:
        text = "Uusi tapahtuma!!\n"
        text += form_message(ev)
        text += "\n\n"
        messages.append(text)
    for message in messages:
        ok = send_message(bot_token, chat_id, message, parse_mode="Markdown")
        if not ok:
            print("Failed to send message for event:", ev, file=sys.stderr)

    return 0

def post_events(modes = ["month", "dry-run"]) -> int:
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
        text += form_message(ev)
        text += "\n\n"
    if len(events) < 1:
        text += "Ei tapahtumia :("
    
    sent = 0
    if "dry-run" in modes:
        print("DRY-RUN:\n", text)
    else:
        ok = send_message(bot_token, chat_id, text, parse_mode="Markdown")
        if not ok:
            print("Failed to send message for event:", ev, file=sys.stderr)
        else:
            sent += 1

    print(f"Processed {len(events)} events, sent {sent} messages.")
    return 0


def main(argv=None):
    global db, events_url
    parser = argparse.ArgumentParser(description="Simple JSON -> Telegram bot")
    parser.add_argument("--sample", action="store_true", help="Use sample JSON file")
    parser.add_argument("--modes", nargs='+', help="Bot running mode.", required=True)
    args = parser.parse_args(argv)

    modes = args.modes

    if db:
        try:
            db = DB()
            db.ensure_tables()
        except Exception as e:
            print(f"Failed to initialize DB: {e}", file=sys.stderr)
            return 3

    if not bot_token or not chat_id or not events_url:
        print("Please set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and EVENTS_URL environment variables.", file=sys.stderr)
        return 2

    if args.sample:
        events_url = os.environ.get("SAMPLE_URL")

    if "post_events" in modes:
        poll_events()
        post_events(modes=modes)
    elif "poll_events" in modes:
        poll_events()


if __name__ == "__main__":
    sys.exit(main())
