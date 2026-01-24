import logging
import sqlite3
import threading
import time

logger = logging.getLogger('discord_bot')

class DBManager:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row

        # Chroni przed równoległymi zapisami
        self._lock = threading.Lock()

    def initialize_db(self):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS reminder (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                remind_at INTEGER NOT NULL,
                is_sent INTEGER DEFAULT 0
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS league_profiles (
                user_id TEXT PRIMARY KEY,
                riot_id TEXT NOT NULL
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS league_aliases (
                alias TEXT PRIMARY KEY,
                user_id TEXT,
                FOREIGN KEY (user_id)
                REFERENCES league_profiles(user_id)
                ON DELETE CASCADE
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                hour INTEGER,
                temperature REAL,
                wind REAL,
                rainfall REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                station TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """)

            self.conn.commit()

    def get_setting(self, key: str):
        cur = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        )
        row = cur.fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str):
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key)
                DO UPDATE SET value = excluded.value
                """,
                (key, value)
            )
            self.conn.commit()

    def is_telegram_enabled(self) -> bool:
        val = self.get_setting("telegram_enabled")
        return True if val is None else val == "true"

    def set_telegram_enabled(self, enabled: bool):
        self.set_setting(
            "telegram_enabled",
            "true" if enabled else "false"
        )

    def cleanup_old_data(self, days: int = 7):
        """
        Usuwa stare dane historyczne z bazy.
        """
        with self._lock:
            try:
                cur = self.conn.cursor()

                cur.execute(
                    "DELETE FROM weather WHERE timestamp < datetime('now', ?)",
                    (f"-{days} days",)
                )
                weather_deleted = cur.rowcount

                cur.execute(
                    """
                    DELETE FROM reminder
                    WHERE is_sent = 1
                    AND remind_at < ?
                    """,
                    (int(time.time()) - 86400,)
                )
                reminders_deleted = cur.rowcount

                self.conn.commit()

                # VACUUM tylko po commit
                cur.execute("VACUUM")

                return {
                    "weather": weather_deleted,
                    "reminders": reminders_deleted
                }

            except Exception as e:
                self.conn.rollback()
                logger.exception(f"Błąd podczas cleanupu bazy, {e}")
                return None

    def close(self):
        self.conn.close()
