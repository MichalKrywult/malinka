import logging
import sqlite3
import time

logger = logging.getLogger('discord_bot')

class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def initialize_db(self):
        """Tworzy tabele, jeśli nie istnieją"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''PRAGMA journal_mode=WAL;''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS reminder (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            remind_at INTEGER NOT NULL,
            is_sent INTEGER DEFAULT 0
        )''')
       
        cursor.execute('''CREATE TABLE IF NOT EXISTS league_profiles (
            user_id TEXT PRIMARY KEY,
            riot_id TEXT NOT NULL
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS league_aliases (
            alias TEXT PRIMARY KEY,
            user_id TEXT,
            FOREIGN KEY (user_id) REFERENCES league_profiles(user_id) ON DELETE CASCADE
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,           
            hour INTEGER,        
            temperature REAL,    
            wind REAL,           
            rainfall REAL,       
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            station TEXT                             
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')

        conn.commit()
        conn.close()

    def cleanup_old_data(self, days=7):
        """Usuwa stare dane historyczne z bazy."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Czyszczenie tabeli weather
            # SQLite funkcja datetime('now', '-X days') zwraca punkt odniesienia
            cursor.execute(
                "DELETE FROM weather WHERE timestamp < datetime('now', ?)", 
                (f'-{days} days',)
            )
            weather_deleted = cursor.rowcount

            # Wszystkie wysłane i starsze niz 1 dzien (84600 sekund)
            cursor.execute(
                "DELETE FROM reminder WHERE is_sent = 1 AND remind_at < ?",
                (int(time.time()) - (86400 * 1),)
            )
            reminders_deleted = cursor.rowcount

            cursor.execute("VACUUM") 
            conn.commit()
            return {"weather": weather_deleted, "reminders": reminders_deleted}
        except Exception as e:
            print(f"Błąd podczas czyszczenia bazy: {e}")
            logger.error(f"Błąd podczas czyszczenia bazy: {e}")
            return None
        finally:
            conn.close()
    