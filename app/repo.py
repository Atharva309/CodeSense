import os
import sqlite3
from pathlib import Path

# Resolve DB path: env or project root
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("DB_PATH", str(ROOT / "cloudsense.db"))


def _con():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _con() as con:
        c = con.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              delivery_id TEXT UNIQUE,
              event_type TEXT,
              repo TEXT,
              ref TEXT,
              after_sha TEXT,
              created_at TEXT DEFAULT (datetime('now')),
              raw_json TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id INTEGER,
              status TEXT,
              started_at TEXT,
              finished_at TEXT,
              summary_json TEXT,
              FOREIGN KEY(event_id) REFERENCES events(id)
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS findings(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              review_id INTEGER,
              file_path TEXT,
              severity TEXT,
              title TEXT,
              rationale TEXT,
              start_line INTEGER,
              end_line INTEGER,
              patch TEXT
            )
            """
        )
        # Migration: add 'tool' column if it doesn't exist yet
        try:
            c.execute("ALTER TABLE findings ADD COLUMN tool TEXT")
        except sqlite3.OperationalError:
            # Column already exists or old SQLite; ignore
            pass

        con.commit()


def add_event(delivery_id, event_type, repo, ref, after_sha, payload_json):
    with _con() as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO events
             (delivery_id, event_type, repo, ref, after_sha, raw_json)
             VALUES (?, ?, ?, ?, ?, ?)
            """,
            (delivery_id, event_type, repo, ref, after_sha, payload_json),
        )
        if cur.lastrowid:
            return cur.lastrowid
        row = con.execute(
            "SELECT id FROM events WHERE delivery_id=?", (delivery_id,)
        ).fetchone()
        return row["id"]


def list_events(limit: int = 50):
    with _con() as con:
        return con.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def get_latest_review_for_event(event_id: int):
    with _con() as con:
        return con.execute(
            "SELECT * FROM reviews WHERE event_id=? ORDER BY id DESC LIMIT 1",
            (event_id,),
        ).fetchone()


def get_reviews_for_event(event_id: int):
    with _con() as con:
        return con.execute(
            "SELECT * FROM reviews WHERE event_id=? ORDER BY id DESC",
            (event_id,),
        ).fetchall()


def get_findings(review_id: int):
    """Return findings as a list of dicts (not sqlite3.Row)."""
    with _con() as con:
        rows = con.execute(
            "SELECT * FROM findings WHERE review_id=? ORDER BY file_path, severity DESC, id",
            (review_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_review_and_event(review_id: int):
    """Return (review_row, event_row) or (None, None)."""
    with _con() as con:
        review = con.execute(
            "SELECT * FROM reviews WHERE id=?", (review_id,)
        ).fetchone()
        if not review:
            return None, None
        event = con.execute(
            "SELECT * FROM events WHERE id=?", (review["event_id"],)
        ).fetchone()
        return review, event