import json
import logging
import os

import discord
from discord.ext import commands
from utils.leauge_scraper import (  # pyright: ignore[reportMissingImports] 
    fetch_mastery_data,
    fetch_rank_data,
)

logger = logging.getLogger('discord_bot')

class League(commands.Cog):
    def __init__(self, bot, gracze_path):
        self.bot = bot
        self.gracze_path = gracze_path
        self.gracze = self.load_gracze()

    def load_gracze(self):
        if not os.path.exists(self.gracze_path):
            return {}
        with open(self.gracze_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_gracze(self):
        with open(self.gracze_path, "w", encoding="utf-8") as f:
            json.dump(self.gracze, f, indent=4, ensure_ascii=False)

    def resolve_target(self, target: str, mentions: list):
        """Pomocnicza funkcja do ustalania nicku z mentiona lub aliasu."""
        if mentions:
            user_id = str(mentions[0].id)
            return self.gracze.get(user_id, target)
        
        target_lower = target.lower().strip()
        if target_lower in self.gracze:
            return self.gracze[target_lower]
        return target

    # --- Komendy ---

    @commands.command()
    async def dodaj(self, ctx, alias: str, nick_z_tagiem: str):
        if "#" not in nick_z_tagiem:
            await ctx.send("Błąd: Nick musi zawierać tag (np. Nick#EUNE)")
            return
        
        key = str(ctx.message.mentions[0].id) if ctx.message.mentions else alias.lower()
        self.gracze[key] = nick_z_tagiem
        self.save_gracze()
        await ctx.send(f"Zapisano: {alias} -> {nick_z_tagiem}")

    @commands.hybrid_command(name="rank", description="Sprawdza rangę gracza na OP.GG")
    async def rank(self, ctx, cel: str):
        """Sprawdza rangę (wyświetla dywizję, LP i ikonę)."""
        # Defer informuje Discorda, że odpowiedź zajmie chwilę (ważne dla Slash)
        await ctx.defer()
        logger.info(f"Użytkownik {ctx.author} sprawdza rangę: {cel}")

        # Obsługa mentions dla Slash i prefixowych komend
        mentions = ctx.message.mentions if ctx.message else []
        target = self.resolve_target(cel, mentions)

        if "#" not in target:
            await ctx.send("Nieznany gracz lub błędny format. Użyj `Nick#Tag`.")
            return

        data = await fetch_rank_data(target)
        
        if data is None:
            logger.warning(f"Błąd połączenia z OP.GG dla gracza: {target}")
            await ctx.send("Błąd połączenia z OP.GG.")
            return
            
        if not data.get("found"):
            await ctx.send(f"Nie znaleziono danych rankingowych dla {target}.")
            return

        embed = discord.Embed(
            title=f"Profil LoL: {data['nick']}",
            description=f"**{data['tier']}**\n**{data['lp']}**",
            color=discord.Color.blue()
        )
        if data.get('img_url'):
            embed.set_thumbnail(url=data['img_url'])
            
        await ctx.send(embed=embed)

    # KOMENDA MASTERY
    @commands.hybrid_command(name="mastery", description="Pokazuje TOP 3 postacie pod względem punktów maestrii")
    async def mastery(self, ctx, cel: str):
        """Pokazuje TOP 3 postacie pod względem punktów maestrii."""
        await ctx.defer()
        logger.info(f"Użytkownik {ctx.author} sprawdza masterie: {cel}")

        mentions = ctx.message.mentions if ctx.message else []
        target = self.resolve_target(cel, mentions)

        if "#" not in target:
            await ctx.send("Podaj `Nick#Tag` lub dodaj gracza za pomocą `!dodaj`.")
            return

        data = await fetch_mastery_data(target)

        if data is None:
            logger.warning(f"Błąd połączenia z OP.GG dla gracza: {target}")
            await ctx.send("Nie udało się połączyć z OP.GG.")
            return

        if not data:
            await ctx.send("Nie znaleziono danych o mastery. Odśwież profil na OP.GG.")
            return
        
        embed = discord.Embed(
            title=f"TOP Mastery: {target}",
            description="\n".join([f"{line}" for line in data]),
            color=discord.Color.purple()
        )
        embed.set_footer(text="Dane pobrane z OP.GG")

        await ctx.send(embed=embed)


async def setup(bot):
    # Pobiera ścieżkę z configu bota
    path = bot.config['GRACZE_PATH']
    await bot.add_cog(League(bot, path))