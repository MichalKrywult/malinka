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

# Konfiguracja ścieżek i tokena
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "reminder.db")
GRACZE_PATH = os.path.join(DATA_DIR, "gracze.json")

logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO)
# RotatingFileHandler zapobiega zapchaniu karty SD 
# Gdy plik osiągnie 5MB, tworzy nowy (trzyma max 3 kopie)
log_path = os.path.join(DATA_DIR, 'bot.log')
handler = RotatingFileHandler(
    filename=log_path, 
    encoding='utf-8', 
    maxBytes=5 * 1024 * 1024, 
    backupCount=3
)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# logowanie na konsolę,
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(console_handler)

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Setup bota
intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        # Przekazujemy config do bota, żeby Cogi miały do niego dostęp
        self.config = {
            'BASE_DIR': BASE_DIR,
            'DB_PATH': DB_PATH,
            'GRACZE_PATH': GRACZE_PATH
        }

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
        await self.tree.sync()
        print("Komendy zsynchronizowane.")

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