import json
import os
import random
import sqlite3
import time
from datetime import datetime

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import ui
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "reminder", "data", "reminder.db")
GRACZE = "discord_bot/gracze.json"

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Ensure the required directories exist
if not os.path.exists(os.path.join(BASE_DIR, "reminder", "data")):
    os.makedirs(os.path.join(BASE_DIR, "reminder", "data"))

# Reminder Modal for adding reminders
class ReminderModal(ui.Modal, title='Dodaj Przypomnienie'):
    # Input fields for date, time, year, and reminder text
    data_input = ui.TextInput(
        label='Dzień i Miesiąc',
        placeholder='DD.MM (np. 30.12)',
        min_length=5, max_length=5,
        default=datetime.now().strftime("%d.%m")  # Default to today's date
    )
    godzina_input = ui.TextInput(
        label='Godzina',
        placeholder='HH:MM (np. 12:30)',
        min_length=5, max_length=5
    )
    rok_input = ui.TextInput(
        label='Rok',
        default=str(datetime.now().year),
        min_length=4, max_length=4
    )
    tresc_input = ui.TextInput(
        label='O czym Ci przypomnieć?',
        style=discord.TextStyle.paragraph,
        placeholder='Treść przypomnienia...',
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # Construct the full date and time string
        data_str = self.data_input.value  # DD.MM
        godzina_str = self.godzina_input.value  # HH:MM
        rok_str = self.rok_input.value  # YYYY
        tresc = self.tresc_input.value
        
        try:
            # Combine into a single string for datetime parsing
            pelna_data = f"{data_str}.{rok_str} {godzina_str}"
            dt_obj = datetime.strptime(pelna_data, "%d.%m.%Y %H:%M")
            
            now = datetime.now()
            if dt_obj < now:
                await interaction.response.send_message("Ta data już minęła!", ephemeral=True)
                return

            remind_at = int(dt_obj.timestamp())

            # Save reminder to database
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO reminder (user_id, content, remind_at) VALUES (?, ?, ?)", 
                         (user_id, tresc, remind_at))
            conn.commit()
            conn.close()

            await interaction.response.send_message(
                f"Zapisane, przypomnienie o **{tresc}** na {dt_obj.strftime('%d.%m.%Y o %H:%M')}.", 
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                "Błędny format! Upewnij się, że wpisałeś np. 30.12 i 15:00", 
                ephemeral=True
            )

# Helper function to create embeds
def create_embed(title, description, color, footer):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text=footer)
    return embed

# Create reminder table if it doesn't exist
def create_reminder_table_if_non_existent():
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

@bot.event
async def on_ready():
    await bot.tree.sync()
    create_reminder_table_if_non_existent()
    print(f'Zalogowano jako {bot.user}')
    if not check_reminder.is_running():
        check_reminder.start()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Nieznana komenda")

# Manage players
def laduj_graczy():
    if not os.path.exists(GRACZE):
        return {}
    with open(GRACZE, "r", encoding="utf-8") as f:
        return json.load(f)

def zapisz_graczy(dane):
    with open(GRACZE, "w", encoding="utf-8") as f:
        json.dump(dane, f, indent=4, ensure_ascii=False)

# --- FUNKCJE LOGICZNE ---

async def get_rank(cel: str, mentions=None):
    gracze = laduj_graczy()
    cel_lower = cel.lower().strip()
    nick_z_tagiem = cel

    if mentions and len(mentions) > 0:
        user_id = str(mentions[0].id)
        nick_z_tagiem = gracze.get(user_id, cel)
    elif cel_lower in gracze:
        nick_z_tagiem = gracze[cel_lower]

    if "#" not in nick_z_tagiem:
        return "Nieznany gracz. Użyj `!dodaj` lub podaj `Nick#Tag`."

    name_tag = nick_z_tagiem.replace("#", "-")
    url = f"https://www.op.gg/lol/summoners/eune/{name_tag}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return "Nie znaleziono gracza na OP.GG."
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                lp_span = None
                for s in soup.find_all("span"):
                    txt = s.get_text()
                    if txt and "LP" in txt: 
                        lp_span = s
                        break 

                if not lp_span:
                    return f"Gracz **{nick_z_tagiem}** nie ma rangi lub profil wymaga odświeżenia."

                lp_text = lp_span.get_text(strip=True)

                tier_text = "RANKED"
                parent_div = lp_span.find_parent("div")
                if parent_div:
                    tier_el = parent_div.find("strong")
                    if tier_el: 
                        tier_text = tier_el.get_text(strip=True)

                wr_text = "Brak danych o WR"
                context_area = lp_span.find_parent("div")
                for _ in range(3):
                    if context_area:
                        for s in context_area.find_all("span"):
                            s_txt = s.get_text()
                            if s_txt and "Win rate" in s_txt:
                                wr_text = s_txt.strip()
                                break
                        context_area = context_area.find_parent("div")

                embed = create_embed(
                    title=f"Profil LoL: {nick_z_tagiem}",
                    description=f"**{tier_text.upper()}**\n**{lp_text}**\n{wr_text}",
                    color=discord.Color.blue(),
                    footer="Dane pobrane z OP.GG"
                )

                for img in soup.find_all("img"):
                    src = img.get('src') 
                    if src and isinstance(src, str) and "medals_new" in src:
                        final_url = src if src.startswith('http') else f"https:{src}"
                        embed.set_thumbnail(url=final_url)
                        break
                
                return embed

    except Exception as e:
        print(f"Błąd logiki rank: {e}")
        return "Wystąpił błąd podczas analizy strony OP.GG."

async def get_mastery(cel: str, mentions=None):
    """Główny silnik scrapujący mastery z OP.GG"""
    gracze = laduj_graczy()
    cel_lower = cel.lower().strip()
    nick_z_tagiem = cel

    # Obsługa aliasów i pingów
    if mentions and len(mentions) > 0:
        user_id = str(mentions[0].id)
        nick_z_tagiem = gracze.get(user_id, cel)
    elif cel_lower in gracze:
        nick_z_tagiem = gracze[cel_lower]

    if "#" not in nick_z_tagiem:
        return "Podaj `Nick#Tag` lub dodaj gracza za pomocą `!dodaj`."

    name_tag = nick_z_tagiem.replace("#", "-")
    url = f"https://www.op.gg/lol/summoners/eune/{name_tag}/mastery"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return "Nie udało się połączyć z OP.GG. Sprawdź, czy nick jest poprawny."
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Szukanie kontenerów z bohaterami
                containers = soup.find_all("div", attrs={"data-tooltip-id": "opgg-tooltip"})
                
                mastery_list = []
                for container in containers:
                    name_el = container.find("span", class_="text-gray-900")
                    if name_el:
                        name = name_el.get_text(strip=True)
                        if "Link" in name or "Total" in name:
                            continue
                        
                        points_el = container.find("span", class_="text-gray-500")
                        level_el = container.find("span", class_="text-2xs")
                        
                        pts = points_el.get_text(strip=True).replace('\xa0', ' ') if points_el else "?"
                        lvl = level_el.get_text(strip=True) if level_el else "?"
                        
                        mastery_list.append(f"{len(mastery_list)+1}. **{name}** (Lvl {lvl}) — `{pts} pkt`")
                    
                    if len(mastery_list) >= 3:
                        break

                if not mastery_list:
                    return "Nie znaleziono danych o mastery. Może profil nie był dawno odświeżany?"

                return create_embed(
                    title=f"TOP Mastery: {nick_z_tagiem}",
                    description="\n".join(mastery_list),
                    color=discord.Color.purple(),
                    footer="Dane pobrane z OP.GG"
                )

    except Exception as e:
        print(f"Błąd mastery: {e}")
        return "Wystąpił błąd podczas analizy strony mastery."

# --- KOMENDY ---

@bot.tree.command(name="przypomnij", description="Otwiera okno dodawania przypomnienia")
async def przypomnij(interaction: discord.Interaction):
    await interaction.response.send_modal(ReminderModal())

@bot.command(name="rank")
async def rank_text(ctx, *, cel: str):
    """Sprawdza rangę (komenda tekstowa)"""
    wynik = await get_rank(cel, ctx.message.mentions)
    if isinstance(wynik, discord.Embed):
        await ctx.send(embed=wynik)
    else:
        await ctx.send(wynik)

@bot.tree.command(name="rank", description="Sprawdza rangę gracza na OP.GG")
async def rank_slash(interaction: discord.Interaction, cel: str):
    """Sprawdza rangę (komenda slash)"""
    await interaction.response.defer()
    wynik = await get_rank(cel)
    if isinstance(wynik, discord.Embed):
        await interaction.followup.send(embed=wynik)
    else:
        await interaction.followup.send(wynik)

@bot.command(name="mastery")
async def mastery_text(ctx, *, cel: str):
    """Pokazuje TOP 3 postacie (tekstowo)"""
    wynik = await get_mastery(cel, ctx.message.mentions)
    if isinstance(wynik, discord.Embed):
        await ctx.send(embed=wynik)
    else:
        await ctx.send(wynik)

@bot.tree.command(name="mastery", description="Pokazuje 3 postacie z największym poziomem maestrii")
async def mastery_slash(interaction: discord.Interaction, cel: str):
    """Pokazuje TOP 3 postacie (slash command)"""
    await interaction.response.defer() 
    wynik = await get_mastery(cel)
    if isinstance(wynik, discord.Embed):
        await interaction.followup.send(embed=wynik)
    else:
        await interaction.followup.send(wynik)

@bot.command()
async def dodaj(ctx, alias: str, nick_z_tagiem: str):
    """Dodaje gracza do bazy. Użycie: !dodaj franek Nick#Tag lub !dodaj @ping Nick#Tag"""
    if "#" not in nick_z_tagiem:
        await ctx.send("Błąd: Nick musi zawierać tag (np. Nick#EUNE)")
        return
    gracze = laduj_graczy()
    if ctx.message.mentions:
        klucz = str(ctx.message.mentions[0].id)
    else:
        klucz = alias.lower()
    gracze[klucz] = nick_z_tagiem
    zapisz_graczy(gracze)
    await ctx.send(f"Powiązano **{alias}** z kontem **{nick_z_tagiem}**!")

@bot.command()
async def kostka(ctx):
    """Rzut kostka K6"""
    wynik = random.randint(1, 6)
    wybrany_kolor = discord.Color.green() if wynik % 2 == 0 else discord.Color.red()
    embed = create_embed(
        "Rzut kostką K6",
        f"Wyrzuciłeś: **{wynik}**",
        wybrany_kolor,
        f"Wywołane przez {ctx.author.name}"
    )
    await ctx.send(embed=embed)

@bot.command()
async def awatar(ctx,member: discord.Member | None = None):
    """Daje awatar po !awatar @uzytkownik \n dla samego !awatar daje awatar autora"""
    user = member or ctx.author
    embed = create_embed(
        f"Awatar użytkownika {user}",
        "Aktualny awatar:",
        discord.Color.green(),
        ""
    )
    embed.set_image(url=user.display_avatar.url)
    await ctx.send(embed=embed)

# --- TASKS ---

@tasks.loop(seconds=60)
async def check_reminder():
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, content FROM reminder WHERE remind_at <= ? AND is_sent = 0", (now,))
    pending = cursor.fetchall()
    for rem_id, user_id, content in pending:
        user = await bot.fetch_user(user_id)
        if user:
            try:
                await user.send(f"{content}")
                cursor.execute("UPDATE reminder SET is_sent = 1 WHERE id = ?", (rem_id,))
            except Exception as e:
                print(f"Nie udało się wysłać wiadomości do {user_id}: {e}")
    conn.commit()
    conn.close()

if TOKEN is None:
    print("Brak tokena w pliku .env")
else:
    bot.run(TOKEN)