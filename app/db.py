"""SQLite storage. Each booked hour is a row in booking_slots with a UNIQUE
(master_id, day, hour) constraint, so double-booking is impossible even under
concurrent requests."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id  TEXT NOT NULL,
    master_id   TEXT NOT NULL,
    day         TEXT NOT NULL,
    start_hour  INTEGER NOT NULL,
    hours       INTEGER NOT NULL,
    client_name TEXT NOT NULL,
    phone       TEXT NOT NULL,
    comment     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS booking_slots (
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    master_id  TEXT NOT NULL,
    day        TEXT NOT NULL,
    hour       INTEGER NOT NULL,
    UNIQUE (master_id, day, hour)
);
"""


class SlotTaken(Exception):
    """Raised when at least one requested hour is already booked."""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def busy_hours(self, master_id: str, day: str) -> set[int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT hour FROM booking_slots WHERE master_id = ? AND day = ?",
                (master_id, day),
            ).fetchall()
        return {r["hour"] for r in rows}

    def create_booking(self, *, service_id: str, master_id: str, day: str,
                       start_hour: int, hours: int, client_name: str,
                       phone: str, comment: str) -> int:
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                cur = conn.execute(
                    "INSERT INTO bookings (service_id, master_id, day, start_hour,"
                    " hours, client_name, phone, comment) VALUES (?,?,?,?,?,?,?,?)",
                    (service_id, master_id, day, start_hour, hours,
                     client_name, phone, comment),
                )
                booking_id = cur.lastrowid
                conn.executemany(
                    "INSERT INTO booking_slots (booking_id, master_id, day, hour)"
                    " VALUES (?,?,?,?)",
                    [(booking_id, master_id, day, h)
                     for h in range(start_hour, start_hour + hours)],
                )
                conn.execute("COMMIT")
                return booking_id
            except sqlite3.IntegrityError as exc:
                conn.execute("ROLLBACK")
                raise SlotTaken from exc
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def list_bookings(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM bookings ORDER BY day, start_hour, master_id"
            ).fetchall()
        return [dict(r) for r in rows]
