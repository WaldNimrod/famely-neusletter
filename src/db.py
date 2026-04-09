"""
Famely Neuslettr — Database Layer
SQLite helpers per LOD400 §9.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger('famely.db')


class Database:
    """SQLite database wrapper with schema init and query helpers."""

    def __init__(self, db_path: str = "data/famely.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        """Create all tables on first run."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS content_archive (
                id              TEXT PRIMARY KEY,
                url             TEXT UNIQUE NOT NULL,
                title           TEXT NOT NULL,
                source_name     TEXT,
                source_type     TEXT,
                source_url      TEXT,
                source_trust    REAL DEFAULT 0.7,
                published_at    TEXT,
                fetched_at      TEXT NOT NULL,
                language        TEXT NOT NULL CHECK(language IN ('he', 'en')),
                raw_text        TEXT,
                tags            TEXT,
                image_url       TEXT,
                content_hash    TEXT NOT NULL,
                is_submission   INTEGER NOT NULL DEFAULT 0,
                submitted_by    TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS newsletters (
                date            TEXT PRIMARY KEY,
                status          TEXT NOT NULL DEFAULT 'building'
                                CHECK(status IN ('building','ready','build_failed',
                                      'distributed','send_failed','feedback_collecting','completed')),
                greeting        TEXT,
                puzzle          TEXT,
                puzzle_answer   TEXT,
                survey_question TEXT,
                html_path       TEXT,
                public_url      TEXT,
                items_fetched   INTEGER,
                items_selected  INTEGER,
                sources_scanned INTEGER,
                submissions_count INTEGER DEFAULT 0,
                build_duration_ms INTEGER,
                neo_json        TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS newsletter_items (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                newsletter_date TEXT NOT NULL REFERENCES newsletters(date),
                member_id       TEXT NOT NULL,
                content_id      TEXT NOT NULL,
                headline        TEXT,
                summary         TEXT,
                category        TEXT,
                score           REAL,
                position        INTEGER,
                is_discovery    INTEGER DEFAULT 0,
                is_submission   INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS family_submissions (
                id              TEXT PRIMARY KEY,
                member_id       TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                message_type    TEXT NOT NULL CHECK(message_type IN ('text','image','video','document','link')),
                content_text    TEXT,
                media_local_path TEXT,
                media_mime_type TEXT,
                media_size_bytes INTEGER,
                link_url        TEXT,
                status          TEXT NOT NULL DEFAULT 'received'
                                CHECK(status IN ('received','editing','published','rejected','edit_failed')),
                edited_headline TEXT,
                edited_summary  TEXT,
                edition_date    TEXT,
                retry_count     INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id       TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                type            TEXT NOT NULL CHECK(type IN ('survey', 'text')),
                newsletter_date TEXT,
                value           TEXT,
                article_id      TEXT,
                source_detail   TEXT
            );

            CREATE TABLE IF NOT EXISTS token_usage (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT NOT NULL,
                module          TEXT NOT NULL,
                operation       TEXT NOT NULL,
                model           TEXT NOT NULL,
                input_tokens    INTEGER NOT NULL,
                output_tokens   INTEGER NOT NULL,
                cost_usd        REAL NOT NULL,
                newsletter_date TEXT
            );

            CREATE TABLE IF NOT EXISTS scan_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT NOT NULL,
                source_id       TEXT NOT NULL,
                items_found     INTEGER DEFAULT 0,
                items_new       INTEGER DEFAULT 0,
                errors          TEXT,
                duration_ms     INTEGER,
                http_status     INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_content_hash ON content_archive(content_hash);
            CREATE INDEX IF NOT EXISTS idx_content_date ON content_archive(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_items_date ON newsletter_items(newsletter_date, member_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_date ON feedback(newsletter_date, member_id);
            CREATE INDEX IF NOT EXISTS idx_submissions_status ON family_submissions(status);
            CREATE INDEX IF NOT EXISTS idx_token_date ON token_usage(timestamp);
        """)
        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    # ─── Content Archive ──────────────────────────────────────

    def get_recent_hashes(self, days: int = 30) -> set[str]:
        """Get content hashes from last N days for dedup."""
        rows = self.conn.execute(
            "SELECT content_hash FROM content_archive WHERE fetched_at > date('now', ?)",
            (f'-{days} days',)
        ).fetchall()
        return {r['content_hash'] for r in rows}

    def archive_nci(self, nci) -> bool:
        """Insert NCI into content_archive. Returns True if new, False if duplicate."""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO content_archive
                (id, url, title, source_name, source_type, source_url, source_trust,
                 published_at, fetched_at, language, raw_text, tags, image_url,
                 content_hash, is_submission, submitted_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nci.id, nci.url, nci.title, nci.source_name, nci.source_type,
                nci.source_url, nci.source_trust, nci.published_at, nci.fetched_at,
                nci.language, nci.raw_text, json.dumps(nci.tags, ensure_ascii=False),
                nci.image_url, nci.content_hash, int(nci.is_submission), nci.submitted_by
            ))
            self.conn.commit()
            return self.conn.total_changes > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to archive NCI {nci.id}: {e}")
            return False

    # ─── Newsletters ──────────────────────────────────────────

    def create_newsletter(self, date: str, status: str = 'building') -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO newsletters (date, status) VALUES (?, ?)",
            (date, status)
        )
        self.conn.commit()

    def update_newsletter(self, date: str, **kwargs) -> None:
        sets = ', '.join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [date]
        self.conn.execute(
            f"UPDATE newsletters SET {sets}, updated_at = datetime('now') WHERE date = ?",
            vals
        )
        self.conn.commit()

    def get_newsletter(self, date: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM newsletters WHERE date = ?", (date,)
        ).fetchone()
        return dict(row) if row else None

    def get_last_newsletter(self) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM newsletters ORDER BY date DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    # ─── Newsletter Items ─────────────────────────────────────

    def insert_newsletter_item(self, newsletter_date: str, member_id: str,
                                content_id: str, headline: str, summary: str,
                                category: str, score: float, position: int,
                                is_discovery: bool = False, is_submission: bool = False):
        self.conn.execute("""
            INSERT INTO newsletter_items
            (newsletter_date, member_id, content_id, headline, summary,
             category, score, position, is_discovery, is_submission)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (newsletter_date, member_id, content_id, headline, summary,
              category, score, position, int(is_discovery), int(is_submission)))
        self.conn.commit()

    # ─── Family Submissions ───────────────────────────────────

    def insert_submission(self, sub) -> None:
        self.conn.execute("""
            INSERT INTO family_submissions
            (id, member_id, timestamp, message_type, content_text,
             media_local_path, media_mime_type, media_size_bytes, link_url,
             status, edited_headline, edited_summary, edition_date, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sub.id, sub.member_id, sub.timestamp, sub.message_type,
              sub.content_text, sub.media_local_path, sub.media_mime_type,
              sub.media_size_bytes, sub.link_url, sub.status,
              sub.edited_headline, sub.edited_summary, sub.edition_date,
              sub.retry_count))
        self.conn.commit()

    def get_pending_submissions(self, cutoff_time: Optional[str] = None):
        query = "SELECT * FROM family_submissions WHERE status IN ('received', 'edit_failed')"
        params = ()
        if cutoff_time:
            query += " AND timestamp < ?"
            params = (cutoff_time,)
        query += " ORDER BY timestamp ASC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def update_submission(self, sub_id: str, **kwargs) -> None:
        sets = ', '.join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [sub_id]
        self.conn.execute(
            f"UPDATE family_submissions SET {sets}, updated_at = datetime('now') WHERE id = ?",
            vals
        )
        self.conn.commit()

    # ─── Feedback ─────────────────────────────────────────────

    def insert_feedback(self, event) -> None:
        self.conn.execute("""
            INSERT INTO feedback (member_id, timestamp, type, newsletter_date, value, article_id, source_detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event.member_id, event.timestamp, event.type,
              event.newsletter_date, event.value, event.article_id,
              event.source_detail))
        self.conn.commit()

    def has_recent_survey(self, member_id: str, hours: int = 6) -> bool:
        row = self.conn.execute("""
            SELECT COUNT(*) as cnt FROM feedback
            WHERE member_id = ? AND type = 'survey'
            AND timestamp > datetime('now', ?)
        """, (member_id, f'-{hours} hours')).fetchone()
        return row['cnt'] > 0

    # ─── Token Usage ──────────────────────────────────────────

    def log_token_usage(self, timestamp: str, module: str, operation: str,
                         model: str, input_tokens: int, output_tokens: int,
                         cost_usd: float, newsletter_date: Optional[str] = None):
        self.conn.execute("""
            INSERT INTO token_usage
            (timestamp, module, operation, model, input_tokens, output_tokens,
             cost_usd, newsletter_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, module, operation, model, input_tokens, output_tokens,
              cost_usd, newsletter_date))
        self.conn.commit()

    def get_daily_cost(self, date: str) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) as total FROM token_usage WHERE newsletter_date = ?",
            (date,)
        ).fetchone()
        return row['total']

    def get_monthly_cost(self, year_month: str) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) as total FROM token_usage WHERE newsletter_date LIKE ?",
            (f'{year_month}%',)
        ).fetchone()
        return row['total']

    # ─── Scan Log ─────────────────────────────────────────────

    def log_scan(self, date: str, source_id: str, items_found: int,
                  items_new: int, errors: Optional[str], duration_ms: int,
                  http_status: Optional[int]):
        self.conn.execute("""
            INSERT INTO scan_log (date, source_id, items_found, items_new, errors, duration_ms, http_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date, source_id, items_found, items_new, errors, duration_ms, http_status))
        self.conn.commit()

    # ─── Utility ──────────────────────────────────────────────

    def close(self):
        self.conn.close()
