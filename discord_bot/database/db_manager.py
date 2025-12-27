import sqlite3


class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def initialize_db(self):
        """Tworzy tabele, jeśli nie istnieje"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS reminder (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            remind_at INTEGER NOT NULL,
            is_sent INTEGER DEFAULT 0
        )''')
       
        cursor.execute('''CREATE TABLE IF NOT EXISTS league_profiles (
        user_id TEXT,             
        riot_id TEXT NOT NULL,
        alias TEXT UNIQUE,        
        UNIQUE(user_id)           
        )''')
        conn.commit()
        conn.close()
