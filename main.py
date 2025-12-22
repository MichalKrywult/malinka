import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

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

if TOKEN is None:
    print("Brak tokena w pliku .env")
else:
    bot.run(TOKEN)