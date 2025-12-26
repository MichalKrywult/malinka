import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "reminder.db")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


cursor.execute('''CREATE TABLE IF NOT EXISTS reminder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    remind_at INTEGER NOT NULL,
    is_sent INTEGER DEFAULT 0
)''')

conn.commit()
conn.close()