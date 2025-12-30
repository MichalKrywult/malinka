import logging

import aiohttp
import discord
from discord.ext import commands
from utils.leauge_scraper import (
    fetch_mastery_data,
    fetch_rank_data,
)

logger = logging.getLogger('discord_bot')
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

class League(commands.Cog):
    def __init__(self, bot,db_manager):
        self.bot = bot
        self.db = db_manager
        self.session = None
    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(headers=HEADERS)
        return await super().cog_load()
    
    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()
        return await super().cog_unload()

    def resolve_target(self, target: str, mentions: list):
        # Wyciąga ID jeśli jest wzmianka
        search_term = str(mentions[0].id) if mentions else target.strip()
        clean_id = search_term.replace("<@", "").replace("!", "").replace(">", "").replace("&", "")

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            #LOWER zeby na pewno działało dla dużych i małych liter
            cursor.execute('''
                SELECT lp.riot_id 
                FROM league_profiles lp
                LEFT JOIN league_aliases la ON lp.user_id = la.user_id
                WHERE lp.user_id = ? OR LOWER(la.alias) = LOWER(?)
                LIMIT 1
            ''', (clean_id, target.lower()))
            
            row = cursor.fetchone()
            
            # Jeśli znaleziono w bazie, zwraca riot_id. 
            # Jeśli NIE znaleziono, zwraca oryginał (Nick#Tag)
            return row[0] if (row and row[0]) else target
        except Exception as e:
            logger.error(f"Błąd bazy w resolve_target: {e}")
            return target
        finally:
            conn.close()
    
    @commands.command(name="aliasy", description="Pokazuje listę wszystkich aliasów w systemie")
    async def aliasy(self, ctx):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            # Pobiera wszystkie aliasy i przypisane do nich Riot ID
            # JOIN,  Nick#Tag pod aliasem
            cursor.execute('''
                SELECT la.alias, lp.riot_id 
                FROM league_aliases la
                JOIN league_profiles lp ON la.user_id = lp.user_id
            ''')
            rows = cursor.fetchall()
            
            if not rows:
                await ctx.send("Baza aliasów jest obecnie pusta.")
                return

            # lista i sort
            rows.sort(key=lambda x: x[0])
            
            tekst = ""
            for alias, riot_id in rows:
                # tylko tekstowe aliasy, bez @
                if not alias.isdigit():
                    tekst += f"• `{alias}` ➔ **{riot_id}**\n"

            if not tekst:
                tekst = "Brak tekstowych aliasów (tylko powiązania z ID)."

            embed = discord.Embed(
                title="Wszystkie aliasy",
                description=tekst,
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Błąd w komendzie aliasy: {e}")
            await ctx.send("Wystąpił błąd podczas pobierania listy.")
        finally:
            conn.close()

    @commands.command(name="dodaj")
    async def dodaj(self, ctx, alias_lub_mention: str, nick_z_tagiem: str):
        if "#" not in nick_z_tagiem:
            await ctx.send(" Użyj formatu `Nick#Tag`.")
            return

        # Jeśli pierwszy argument to @
        if ctx.message.mentions:
            target_id = str(ctx.message.mentions[0].id)
            final_alias = target_id 
        else:
            # Jeśli to tekst np. !dodaj Franek 
            # alias jako unikalny identyfikatora w tabeli profili 
            # zamiast dc_id.
            target_id = alias_lub_mention.lower()
            final_alias = target_id

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            # stworzenie profilu Ligi
            cursor.execute('''
                INSERT OR REPLACE INTO league_profiles (user_id, riot_id) 
                VALUES (?, ?)
            ''', (target_id, nick_z_tagiem))
            
            # ... oraz jego aliasu
            cursor.execute('''
                INSERT OR IGNORE INTO league_aliases (alias, user_id) 
                VALUES (?, ?)
            ''', (final_alias, target_id))
            
            conn.commit()
            
            msg = f"Powiązano `{nick_z_tagiem}` ze skrótem `{final_alias}`"
            if target_id.isdigit():
                msg = f"Powiązano `{nick_z_tagiem}` z kontem <@{target_id}>"
            
            await ctx.send(msg)
        except Exception as e:
            logger.error(f"Błąd w dodaj: {e}")
            await ctx.send(" Błąd bazy danych.")
        finally:
            conn.close()

    #KOMENDA RANK
    @commands.hybrid_command(name="rank", description="Sprawdza rangę gracza na OP.GG")
    async def rank(self, ctx, cel: str):
        """Sprawdza rangę w Lidze"""
        # Defer informuje Discorda, że odpowiedź zajmie chwilę (ważne dla Slash)
        await ctx.defer()
        logger.info(f"Użytkownik {ctx.author} sprawdza rangę: {cel}")

        # Obsługa mentions dla Slash i prefixowych komend
        
        mentions = ctx.message.mentions if (ctx.message and ctx.message.mentions) else []
        target = self.resolve_target(cel, mentions)

        if "#" not in target:
            await ctx.send("Nieznany gracz lub błędny format. Użyj `Nick#Tag`.")
            return

        if self.session is not None:
            data = await fetch_rank_data(self.session ,target)
        else:
            await ctx.send("Błąd sesji")
            return
        
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
        """Pokazuje TOP 3 postacie pod względem punktów maestrii"""
        await ctx.defer()
        logger.info(f"Użytkownik {ctx.author} sprawdza masterie: {cel}")

        # Obsługa mentions dla Slash i prefixowych komend
        mentions = ctx.message.mentions if (ctx.message and ctx.message.mentions) else []
        target = self.resolve_target(cel, mentions)

        if "#" not in target:
            await ctx.send("Podaj `Nick#Tag` lub dodaj gracza za pomocą `!dodaj`.")
            return
        if self.session is not None:
            data = await fetch_mastery_data(self.session ,target)
        else:
            await ctx.send("Błąd sesji")
            return
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
    await bot.add_cog(League(bot, bot.db))