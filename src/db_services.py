"""
Database services for events.
"""
from __future__ import annotations

import os
import json
import hashlib
import datetime
from typing import Any, Dict

from sqlalchemy import DateTime, Index, Text, create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DATABASE_URL = os.environ["DATABASE_URL"]


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str | None] = mapped_column(Text)
    event_hash: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    starts_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


Index("events_event_hash_idx", Event.event_hash, unique=True)
Index("events_starts_at_idx", Event.starts_at)
Index(
    "events_event_id_idx",
    Event.event_id,
    unique=True,
    postgresql_where=Event.event_id.is_not(None),
)


def _engine_url(url: str):
    parsed = make_url(url)
    if parsed.drivername == "postgres":
        parsed = parsed.set(drivername="postgresql+psycopg2")
    return parsed


class DB:
    def __init__(self):
        self.engine = create_engine(_engine_url(DATABASE_URL))

    def ensure_tables(self) -> None:
        """
        Ensure all tables exist and are consistent.
        """
        Base.metadata.create_all(self.engine)

    @staticmethod
    def _event_hash(ev: Dict[str, Any]) -> str:
        s = json.dumps(ev, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def save_event_if_new(self, event: Dict[str, Any], starts_at: datetime.datetime | None) -> bool:
        """
        Save event if it's new. Returns True if new, False if already existed.

        Uses either `id`,`event_id`,`url` as event_id when available, otherwise relies on hash.
        `starts_at` is used by date queries, events saved without it are never returned by them.
        """
        event_id = None
        for key in ("id", "event_id", "url"):
            if value := event.get(key):
                event_id = str(value)
                break

        statement = (
            insert(Event)
            .values(
                event_id=event_id,
                event_hash=self._event_hash(event),
                payload=event,
                starts_at=starts_at,
            )
            .on_conflict_do_nothing()
            .returning(Event.id)
        )

        with Session(self.engine) as session, session.begin():
            return session.execute(statement).scalar_one_or_none() is not None

    def get_events_end(self, start: datetime.datetime, end: datetime.datetime) -> list:
        """
        Return list of event payloads that fall between start and end.

        - `start` should be a `datetime.datetime`.
        - `end` may be a `datetime.datetime`.

        Returns a list of Python dicts (the JSON payloads).
        """
        statement = (
            select(Event.payload)
            .where(Event.starts_at.between(start, end))
            .order_by(Event.starts_at.asc())
        )

        with Session(self.engine) as session:
            return list(session.scalars(statement))

    def get_events_delta(self, start: datetime.datetime, delta: datetime.timedelta) -> list:
        """
        Return list of event payloads that fall between start and start+delta.

        - `start` should be a `datetime.datetime`.
        - `delta` may be a `datetime.timedelta`.

        Returns a list of Python dicts (the JSON payloads).
        """
        end = start + delta

        return self.get_events_end(start, end)
