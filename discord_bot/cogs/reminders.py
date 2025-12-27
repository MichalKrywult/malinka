import os
import sqlite3
import time
from datetime import datetime

import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
from utils.telegram_notifier import send_telegram_msg

OWNER_DISCORD_ID = os.getenv('OWNER_DISCORD_ID')

class ReminderModal(ui.Modal, title='Dodaj Przypomnienie'):
    data_input = ui.TextInput(label='Dzień i Miesiąc', placeholder='DD.MM', min_length=5, max_length=5, default=datetime.now().strftime("%d.%m"))
    godzina_input = ui.TextInput(label='Godzina', placeholder='HH:MM', min_length=5, max_length=5)
    rok_input = ui.TextInput(label='Rok', default=str(datetime.now().year), min_length=4, max_length=4)
    tresc_input = ui.TextInput(label='O czym Ci przypomnieć?', style=discord.TextStyle.paragraph, max_length=200)

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pelna_data = f"{self.data_input.value}.{self.rok_input.value} {self.godzina_input.value}"
            dt_obj = datetime.strptime(pelna_data, "%d.%m.%Y %H:%M")
            if dt_obj < datetime.now():
                await interaction.response.send_message("Ta data już minęła!", ephemeral=True)
                return
            
            remind_at = int(dt_obj.timestamp())
            
            conn = sqlite3.connect(self.db_path)
            conn.execute("INSERT INTO reminder (user_id, content, remind_at) VALUES (?, ?, ?)", 
                         (interaction.user.id, self.tresc_input.value, remind_at))
            conn.commit()
            conn.close()

            await interaction.response.send_message("Zapisano przypomnienie!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Błędny format daty!", ephemeral=True)

class Reminders(commands.Cog):
    def __init__(self, bot, db_path):
        self.bot = bot
        self.db_path = db_path
        self.check_reminder.start()

    def cog_unload(self):
        self.check_reminder.cancel()

    @app_commands.command(name="przypomnij", description="Dodaj przypomnienie")
    async def przypomnij(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ReminderModal(self.db_path))

    @tasks.loop(seconds=60)
    async def check_reminder(self):
        # Ważne: czekamy aż bot będzie gotowy zanim zaczniemy sprawdzać DB
        await self.bot.wait_until_ready()
        
        now = int(time.time())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, user_id, content FROM reminder WHERE remind_at <= ? AND is_sent = 0", (now,))
            pending = cursor.fetchall()
            
            for rem_id, user_id, content in pending:
                user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                if user:
                    try:
                        await user.send(f"**Przypomnienie:** {content}")
                        cursor.execute("UPDATE reminder SET is_sent = 1 WHERE id = ?", (rem_id,))
                        if str(user_id)==str(OWNER_DISCORD_ID):
                            try:
                                await send_telegram_msg(content)
                            except Exception as e:
                                print(f"Nie udane wysłanie na Telegrama {e}")
                    except Exception as e:
                        print(f"Błąd wysyłania DM: {e}")
            conn.commit()
        except Exception as e:
            print(f"DB Error: {e}")
        finally:
            conn.close()

async def setup(bot):
    path = bot.config['DB_PATH']
    await bot.add_cog(Reminders(bot, path))