"""
Database services for events.
"""
from __future__ import annotations

import os
import json
import hashlib
import datetime
from typing import Any, Dict

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

class DB:
    def __init__(self):
        pass

    def get_conn(self):
        return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)

    def ensure_tables(self) -> None:
        """
        Ensure all tables exist and are consistent.
        """
        sql = """
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            event_id TEXT,
            event_hash TEXT NOT NULL,
            payload JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS events_event_hash_idx ON events(event_hash);
        CREATE UNIQUE INDEX IF NOT EXISTS events_event_id_idx ON events(event_id) WHERE event_id IS NOT NULL;
        """
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    @staticmethod
    def _event_hash(ev: Dict[str, Any]) -> str:
        s = json.dumps(ev, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def save_event_if_new(self, event: Dict[str, Any]) -> bool:
        """
        Save event if it's new. Returns True if new, False if already existed.

        Uses either `id`,`event_id`,`url` as event_id when available, otherwise relies on hash.
        """
        event_id = None
        for key in ("id", "event_id", "url"):
            if value := event.get(key):
                event_id = str(value)
                break

        ev_hash = self._event_hash(event)

        insert_sql = (
            "INSERT INTO events (event_id, event_hash, payload) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING RETURNING id"
        )

        with self.get_conn() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(insert_sql, (event_id, ev_hash, psycopg2.extras.Json(event)))
                    row = cur.fetchone()
                    conn.commit()
                    return bool(row)
                except Exception:
                    conn.rollback()
                    raise

    def get_events_end(self, start: datetime.datetime, end: datetime.datetime) -> list:
        """
        Return list of event payloads that fall between start and end.

        - `start` should be a `datetime.datetime`.
        - `end` may be a `datetime.datetime`.

        Returns a list of Python dicts (the JSON payloads).
        """
        params = [start, end] * 3

        sql = """
        SELECT
            payload,
            COALESCE(
                (payload->>'start_iso8601')::timestamptz,
                -- Try ISO-like dates first, otherwise try DD/MM/YYYY, else NULL
                CASE
                    WHEN (payload->>'date') ~ '^\\d{4}-' THEN (payload->>'date')::timestamptz
                    WHEN (payload->>'date') ~ '^\\d{2}/\\d{2}/\\d{4}$' THEN to_timestamp(payload->>'date', 'DD/MM/YYYY')::timestamptz
                    ELSE NULL
                END,
                created_at
            ) AS event_time
        FROM events
        WHERE
            (
                (payload->>'start_iso8601')::timestamptz BETWEEN %s AND %s
                OR (
                    CASE
                        WHEN (payload->>'date') ~ '^\\d{4}-' THEN (payload->>'date')::timestamptz
                        WHEN (payload->>'date') ~ '^\\d{2}/\\d{2}/\\d{4}$' THEN to_timestamp(payload->>'date', 'DD/MM/YYYY')::timestamptz
                        ELSE NULL
                    END
                ) BETWEEN %s AND %s
                OR created_at BETWEEN %s AND %s
            )
        ORDER BY event_time ASC;
        """

        with self.get_conn() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                except Exception:
                    cur.execute(
                        "SELECT payload FROM events WHERE created_at BETWEEN %s AND %s ORDER BY created_at ASC",
                        (start, end),
                    )
                    rows = cur.fetchall()

        results = []
        for r in rows:
            payload = r.get("payload") if isinstance(r, dict) else r[0]
            if isinstance(payload, (str, bytes)):
                try:
                    payload = json.loads(payload)
                except Exception:
                    pass
            results.append(payload)

        return results
    
    def get_events_delta(self, start: datetime.datetime, delta: datetime.timedelta) -> list:
        """
        Return list of event payloads that fall between start and start+delta.

        - `start` should be a `datetime.datetime`.
        - `delta` may be a `datetime.timedelta`.

        Returns a list of Python dicts (the JSON payloads).
        """
        end = start + delta

        return self.get_events_end(start, end)