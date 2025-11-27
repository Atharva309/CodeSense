import os
import sqlite3
from pathlib import Path
from typing import Optional

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
        
        # Users table
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              name TEXT,
              created_at TEXT DEFAULT (datetime('now')),
              updated_at TEXT DEFAULT (datetime('now')),
              is_active INTEGER DEFAULT 1
            )
            """
        )
        
        # Repositories table
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              repo_full_name TEXT NOT NULL,
              webhook_secret TEXT UNIQUE NOT NULL,
              webhook_url TEXT,
              github_token TEXT,
              is_active INTEGER DEFAULT 1,
              created_at TEXT DEFAULT (datetime('now')),
              FOREIGN KEY(user_id) REFERENCES users(id),
              UNIQUE(user_id, repo_full_name)
            )
            """
        )
        
        # Events table (existing, but will add user_id and repository_id)
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
        
        # Add user_id and repository_id to events if they don't exist
        try:
            c.execute("ALTER TABLE events ADD COLUMN user_id INTEGER")
            c.execute("ALTER TABLE events ADD COLUMN repository_id INTEGER")
            c.execute("ALTER TABLE events ADD FOREIGN KEY (user_id) REFERENCES users(id)")
            c.execute("ALTER TABLE events ADD FOREIGN KEY (repository_id) REFERENCES repositories(id)")
        except sqlite3.OperationalError:
            # Columns already exist; ignore
            pass
        
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


def add_event(delivery_id, event_type, repo, ref, after_sha, payload_json, user_id=None, repository_id=None):
    """Add an event. user_id and repository_id are optional for backward compatibility."""
    with _con() as con:
        cur = con.cursor()
        # Use INSERT OR IGNORE for SQLite compatibility
        # For PostgreSQL, this would be: INSERT ... ON CONFLICT (delivery_id) DO NOTHING
        cur.execute(
            """
            INSERT OR IGNORE INTO events
             (delivery_id, event_type, repo, ref, after_sha, raw_json, user_id, repository_id)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (delivery_id, event_type, repo, ref, after_sha, payload_json, user_id, repository_id),
        )
        if cur.lastrowid:
            return cur.lastrowid
        row = con.execute(
            "SELECT id FROM events WHERE delivery_id=?", (delivery_id,)
        ).fetchone()
        return row["id"] if row else None


def list_events(limit: int = 50, user_id: Optional[int] = None):
    """List events, optionally filtered by user_id."""
    with _con() as con:
        if user_id:
            return con.execute(
                "SELECT * FROM events WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
            ).fetchall()
        else:
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


# User management functions
def create_user(email: str, password_hash: str, name: str) -> Optional[int]:
    """Create a new user and return user_id."""
    with _con() as con:
        try:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO users (email, password_hash, name)
                VALUES (?, ?, ?)
                """,
                (email, password_hash, name),
            )
            con.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # Email already exists
            return None


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email. Returns dict with password_hash included."""
    with _con() as con:
        row = con.execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        if row:
            return dict(row)
        return None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    with _con() as con:
        row = con.execute(
            "SELECT * FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if row:
            return dict(row)
        return None


# Repository management functions
def create_repository(user_id: int, repo_full_name: str, webhook_secret: str, webhook_url: str, github_token: Optional[str] = None) -> Optional[int]:
    """Create a new repository connection."""
    with _con() as con:
        try:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO repositories (user_id, repo_full_name, webhook_secret, webhook_url, github_token)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, repo_full_name, webhook_secret, webhook_url, github_token),
            )
            con.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # Repository already connected for this user
            return None


def get_repository_by_secret(webhook_secret: str) -> Optional[dict]:
    """Get repository by webhook secret."""
    with _con() as con:
        row = con.execute(
            "SELECT * FROM repositories WHERE webhook_secret=? AND is_active=1", (webhook_secret,)
        ).fetchone()
        if row:
            return dict(row)
        return None


def get_repositories_by_user(user_id: int) -> list[dict]:
    """Get all repositories for a user."""
    with _con() as con:
        rows = con.execute(
            "SELECT * FROM repositories WHERE user_id=? AND is_active=1 ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_repository_by_id(repo_id: int, user_id: int) -> Optional[dict]:
    """Get repository by ID (ensuring it belongs to user)."""
    with _con() as con:
        row = con.execute(
            "SELECT * FROM repositories WHERE id=? AND user_id=?", (repo_id, user_id)
        ).fetchone()
        if row:
            return dict(row)
        return None


def deactivate_repository(repo_id: int, user_id: int) -> bool:
    """Deactivate (disconnect) a repository."""
    with _con() as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE repositories SET is_active=0 WHERE id=? AND user_id=?", (repo_id, user_id)
        )
        con.commit()
        return cur.rowcount > 0