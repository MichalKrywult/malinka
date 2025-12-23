import json
import os
import random

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from dotenv import load_dotenv


def create_embed(title, description, color, footer):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text=footer)
    return embed


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Nieznana komenda")


@bot.command(hidden=True)
async def czesc(ctx):
    await ctx.send(f'Hej {ctx.author.name}!')


@bot.command()
async def kostka(ctx):
    """Rzut kostka K6"""
    wynik = random.randint(1, 6)

    if wynik % 2 == 0:
        wybrany_kolor = discord.Color.green()
    else:
        wybrany_kolor = discord.Color.red()

    embed = create_embed(
        "Rzut kostką K6",
        f"Wyrzuciłeś: **{wynik}**",
        wybrany_kolor,
        f"Wywołane przez {ctx.author.name}"
    )

    await ctx.send(embed=embed)


@bot.command()
async def awatar(ctx,member: discord.Member | None = None):
    """
    Daje awatar po !awatar @uzytkownik \n dla samego !awatar daje awatar autora
    """
    user = member or ctx.author
    embed = create_embed(
        f"Awatar użytkownika {user}",
        "Oto Twój aktualny awatar:",
        discord.Color.green(),
        ""
    )

    embed.set_image(url=user.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(hidden=True)
async def help(ctx):
    lista_komend = ""
    
    for command in bot.commands:
        # Pobiera docstring, jeśli go nie ma to daje 
        if command.hidden: 
            continue
        opis = command.help if command.help else "Brak opisu"
        lista_komend += f"**!{command.name}** - {opis}\n"

    embed = create_embed(
        title="Komendy bota",
        description=lista_komend,
        color=discord.Color.blue(),
        footer=""
    )
    
    await ctx.send(embed=embed)

GRACZE = "gracze.json"
def laduj_graczy():
    if not os.path.exists(GRACZE):
        return {}
    with open( GRACZE, "r", encoding="utf-8") as f:
        return json.load(f)

def zapisz_graczy(dane):
    with open(GRACZE, "w", encoding="utf-8") as f:
        json.dump(dane, f, indent=4, ensure_ascii=False)

@bot.command()
async def dodaj(ctx, alias: str, nick_z_tagiem: str):
    """Dodaje gracza do bazy. Użycie: !dodaj franek Nick#Tag lub !dodaj @ping Nick#Tag"""
    if "#" not in nick_z_tagiem:
        await ctx.send("Błąd: Nick musi zawierać tag (np. Nick#EUNE)")
        return
    
    gracze = laduj_graczy()
    
    # Jeśli oznaczono kogoś, użyj ID jako klucza
    if ctx.message.mentions:
        klucz = str(ctx.message.mentions[0].id)
    else:
        klucz = alias.lower()

    gracze[klucz] = nick_z_tagiem
    zapisz_graczy(gracze)
    
    await ctx.send(f" Powiązano **{alias}** z kontem **{nick_z_tagiem}**!")
@bot.command()
async def rank(ctx, *, cel: str):
    """Sprawdza rangę. format: !rank Nick#Tag, !rank alias lub !rank @ping"""
    
    gracze = laduj_graczy()
    cel_lower = cel.lower().strip()
    nick_z_tagiem = cel

    # Obsługa pingu
    if ctx.message.mentions:
        user_id = str(ctx.message.mentions[0].id)
        if user_id in gracze:
            nick_z_tagiem = gracze[user_id]
        else:
            await ctx.send("Ten użytkownik nie ma przypisanego konta. Użyj: `!dodaj @ping Nick#Tag`.")
            return

    # Obsługa aliasu 
    elif cel_lower in gracze:
        nick_z_tagiem = gracze[cel_lower]

    # walidacja formatu
    if "#" not in nick_z_tagiem:
        await ctx.send("Nie znam tego gracza. Użyj `!dodaj` lub podaj `Nick#Tag`.")
        return

    # Przygotowanie URL
    name_tag = nick_z_tagiem.replace("#", "-")
    url = f"https://www.op.gg/lol/summoners/eune/{name_tag}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await ctx.send("Nie znaleziono gracza. Sprawdź czy nick jest poprawny.")
                    return
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                #bezpiecznye szukanie tekstu
                all_spans = soup.find_all("span")
                lp_span = None
                wr_text = "Brak danych"

                for s in all_spans:
                    txt = s.get_text()
                    if txt:  # Zabezpieczenie przed None/Empty
                        if "LP" in txt and not lp_span:
                            lp_span = s
                        if "Win rate" in txt:
                            wr_text = txt.strip()

                if lp_span:
                    # Szuka nazwy rangi (strong)
                    parent_container = lp_span.find_parent("div")
                    tier_element = None
                    if parent_container:
                        tier_element = parent_container.find("strong")
                    
                    tier_text = tier_element.get_text(strip=True) if tier_element else "UNRANKED"
                    lp_text = lp_span.get_text(strip=True)

                    embed = create_embed(
                        title=f"Profil LoL: {nick_z_tagiem}",
                        description=f"**{tier_text.upper()}**\n**{lp_text}**\n{wr_text}",
                        color=discord.Color.blue(),
                        footer="Dane pobrane z OP.GG"
                    )

                    # BEZPIECZNE SZUKANIE OBRAZKA 
                    all_imgs = soup.find_all("img")
                    for img in all_imgs:
                        src = img.get('src')
                        # Type Guard: sprawdza czy src to string
                        if isinstance(src, str):
                            if "medals_new" in src:
                                # Startswith na bezpiecznym stringu
                                if src.startswith('http'):
                                    final_img_url = src
                                else:
                                    final_img_url = f"https:{src}"
                                
                                embed.set_thumbnail(url=final_img_url)
                                break
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"Gracz **{nick_z_tagiem}** został znaleziony, ale nie posiada rangi (unranked).")
    except Exception as e:
        print(f"Błąd bota: {e}")
        await ctx.send("Wystąpił błąd podczas analizy strony OP.GG.")

if TOKEN is None:
    print("Brak tokena w pliku .env")
else:
    bot.run(TOKEN)
