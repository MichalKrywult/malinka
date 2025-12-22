import os
import random

import discord
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
        "Rzut kostką 🎲",
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
        "System wizualizacji"
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
if TOKEN is None:
    print("Brak tokena w pliku .env")
else:
    bot.run(TOKEN)
