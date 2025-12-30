import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import logging
from logging.handlers import RotatingFileHandler

import discord
from database.db_manager import DBManager  # pyright: ignore[reportMissingImports] 
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# Konfiguracja ścieżek i tokena
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "reminder.db")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


env_log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

# Mapowanie tekstu na stałe logging
log_levels = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

target_level = log_levels.get(env_log_level, logging.INFO)

logger = logging.getLogger('discord_bot')
logger.setLevel(target_level)
# RotatingFileHandler zapobiega zapchaniu karty SD 
# Gdy plik osiągnie 5MB, tworzy nowy (trzyma jedna kopie)
log_path = os.path.join(DATA_DIR, 'bot.log')
handler = RotatingFileHandler(
    filename=log_path, 
    encoding='utf-8', 
    maxBytes=5 * 1024 * 1024, 
    backupCount=1
)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
handler.setLevel(target_level)

# logowanie na konsolę,
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(console_handler)
console_handler.setLevel(target_level)

# Setup bota
intents = discord.Intents.all()
intents.message_content = True
TOKEN = os.getenv('DISCORD_TOKEN')

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        # Przekazujemy config do bota, żeby Cogi miały do niego dostęp
        self.config = {
            'BASE_DIR': BASE_DIR,
            'DB_PATH': DB_PATH
        }

        self.db = DBManager(DB_PATH)
        self.db.initialize_db()
    async def setup_hook(self):
        """Metoda uruchamiana przy starcie, do ładowania rozszerzeń."""
        # Inicjalizacja DB
        db_manager = DBManager(DB_PATH)
        db_manager.initialize_db()

        # Ładowanie Cogów
        cogs = ['cogs.general', 'cogs.league', 'cogs.reminders']
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"Załadowano: {cog}")
            except Exception as e:
                print(f"Nie udało się załadować {cog}: {e}")
        
        # Synchronizacja komend Slash (drzewa komend)
        synch=0
        if synch==1:
            await self.tree.sync()
            print("Komendy zsynchronizowane.")
        else:
            print("Komendy NIE zsynchronizowane.")

    async def on_ready(self):
        # Zabezpieczenie na wypadek, gdyby user nie był jeszcze załadowany
        if self.user is not None:
            print(f'Zalogowano jako {self.user} (ID: {self.user.id})')
        else:
            print('Zalogowano, ale obiekt self.user nie jest jeszcze dostępny.')

# Uruchomienie bota
async def main():
    if not TOKEN:
        print("BRAK TOKENA! Sprawdź plik .env")
        return
    
    bot = MyBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Zatrzymywanie bota")