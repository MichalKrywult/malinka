import logging
import os
import time
from datetime import datetime

import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
from utils.notifer import send_telegram_msg

OWNER_DISCORD_ID = os.getenv('OWNER_DISCORD_ID')

logger = logging.getLogger('discord_bot')

class ReminderModal(ui.Modal, title='Dodaj Przypomnienie'):
    data_input = ui.TextInput(label='Dzień i Miesiąc', placeholder='DD.MM', min_length=5, max_length=5, default=datetime.now().strftime("%d.%m"))
    godzina_input = ui.TextInput(label='Godzina', placeholder='HH:MM', min_length=5, max_length=5)
    rok_input = ui.TextInput(label='Rok', default=str(datetime.now().year), min_length=4, max_length=4)
    tresc_input = ui.TextInput(label='O czym Ci przypomnieć?', style=discord.TextStyle.paragraph, max_length=200)

    def __init__(self, db_manager): # Przyjmuje managera 
        super().__init__()
        self.db = db_manager

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pelna_data = f"{self.data_input.value}.{self.rok_input.value} {self.godzina_input.value}"
            dt_obj = datetime.strptime(pelna_data, "%d.%m.%Y %H:%M")
            if dt_obj < datetime.now():
                await interaction.response.send_message("Ta data już minęła!", ephemeral=True)
                return
            
            remind_at = int(dt_obj.timestamp())
            
            # Używa połączenia z managera
            with self.db.get_connection() as conn:
                conn.execute(
                    "INSERT INTO reminder (user_id, content, remind_at) VALUES (?, ?, ?)", 
                    (interaction.user.id, self.tresc_input.value, remind_at)
                )
                conn.commit()

            await interaction.response.send_message("Zapisano przypomnienie!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Błędny format daty!", ephemeral=True)


class ReminderActionView(ui.View):
    def __init__(self, bot, db_manager, reminder_id, content):
        super().__init__(timeout=None) # Przycisk nie wygasnie 
        self.bot = bot
        self.db = db_manager
        self.reminder_id = reminder_id
        self.content = content

    @ui.button(label="Drzemka (15 min)", style=discord.ButtonStyle.secondary, emoji="⏰")
    async def snooze(self, interaction: discord.Interaction, button: ui.Button):
        new_time = int(time.time() + (15 * 60))
        
        with self.db.get_connection() as conn:
            # Ustawiam nowy czas i reset is_sent na 0
            conn.execute(
                "UPDATE reminder SET remind_at = ?, is_sent = 0 WHERE id = ?", 
                (new_time, self.reminder_id)
            )
            conn.commit()
        
        await interaction.response.edit_message(content=f"Odłożono: **{self.content}** o 15 minut.", view=None)

    @ui.button(label="Zrobione", style=discord.ButtonStyle.success, emoji="✅")
    async def done(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content=f"Zrobione: **{self.content}**", view=None)
        self.stop()

class Reminders(commands.Cog):
    def __init__(self, bot, db_manager): # Konstruktor przyjmuje db_manager
        self.bot = bot
        self.db = db_manager
        self.check_reminder.start()

    def cog_unload(self):
        self.check_reminder.cancel()

    @app_commands.command(name="przypomnij", description="Dodaj przypomnienie")
    async def przypomnij(self, interaction: discord.Interaction):
        # Przekazuje managera do Modala
        await interaction.response.send_modal(ReminderModal(self.db))

    @tasks.loop(seconds=60)
    async def check_reminder(self):
        await self.bot.wait_until_ready()
        
        now = int(time.time())
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT id, user_id, content FROM reminder WHERE remind_at <= ? AND is_sent = 0", 
                    (now,)
                )
                pending = cursor.fetchall()
                
                for rem_id, user_id, content in pending:
                    user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                    if user:
                        try:
                            view = ReminderActionView(self.bot, self.db, rem_id, content)

                            await user.send(f"**Przypomnienie:** {content}",view = view)
                            # Aktualizacja statusu w bazie
                            cursor.execute("UPDATE reminder SET is_sent = 1 WHERE id = ?", (rem_id,))
                            
                            if str(user_id) == str(OWNER_DISCORD_ID):
                                try:
                                    await send_telegram_msg(self.bot,content)
                                except Exception as e:
                                    print(f"Nieudane wysłanie na Telegram: {e}")
                        except Exception as e:
                            print(f"Błąd wysyłania DM do {user_id}: {e}")
                
                conn.commit()
            except Exception as e:
                print(f"Błąd bazy danych w pętli przypomnień: {e}")

async def setup(bot):
    await bot.add_cog(Reminders(bot, bot.db))