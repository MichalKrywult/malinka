import sqlite3


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

        
        try:
            cursor.execute("ALTER TABLE weather ADD COLUMN station TEXT;")
            conn.commit()
            print("Dodano kolumnę 'station' do tabeli weather.")
        except sqlite3.OperationalError:
            pass


        conn.commit()
        conn.close()
