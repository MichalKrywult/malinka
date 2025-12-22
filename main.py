import os
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv


async def create_embed(ctx, title, description, color, footer):
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
intents.message_content = True  # Bez tego bot nie zobaczy "!komenda"
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}')
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Nieznana komenda")

@bot.command()
async def czesc(ctx):
    await ctx.send(f'Hej {ctx.author.name}! ')
@bot.command()
@bot.command()
async def kostka(ctx):
    wynik = random.randint(1, 6)
    if wynik%2==0:
        wybrany_kolor = discord.Color.green()
    else:
           discord.Color.red()
    embed = create_embed(
        "Rzut kostką 🎲", 
        f"Wyrzuciłeś: **{wynik}**", 
        wybrany_kolor, 
        f"Wywołane przez {ctx.author.name}",
        ""
    )    
    await ctx.send(embed=embed)
@bot.command()
async def info(ctx):
    embed= create_embed(
        ctx, 
        "Informacje o bocie", 
        "Bot działa", 
        discord.Color.green(), 
        "stopka"
    )
    await ctx.send(embed=embed)

if TOKEN is None:
    print("Brak tokena w pliku .env")
else:
    bot.run(TOKEN)