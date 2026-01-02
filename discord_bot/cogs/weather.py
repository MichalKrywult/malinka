import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.notifer import send_system_alert
from utils.weather_handler import (
    create_weather_embed,
    fetch_and_save_weather,
    get_latest_weather_from_db,
    get_weather_chart_url,
)

target_time = datetime.time(hour=5, minute=15)
logger = logging.getLogger('discord_bot')

class Weather(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db_path = bot.config['DB_PATH']
        self.daily_weather_report.start()
        self.update_weather_loop.start()

    async def get_forecast_embed(self, city_key: str):
        CITIES = {
            "bielsko": {"name": "Bielsko-Biała", "lat": 49.82, "lon": 19.04},
            "warszawa": {"name": "Warszawa", "lat": 52.23, "lon": 21.01},
            "krakow": {"name": "Kraków", "lat": 50.06, "lon": 19.94},
            "wroclaw": {"name": "Wrocław", "lat": 51.10, "lon": 17.03},
            "poznan": {"name": "Poznań", "lat": 52.41, "lon": 16.92},
            "katowice": {"name": "Katowice", "lat": 50.26, "lon": 19.02},
            "lodz": {"name": "Łódź", "lat": 51.75, "lon": 19.46}
        }

        clean_key = city_key.lower().replace("ł", "l").replace("ó", "o").replace("ń", "n").replace("ź", "z").replace("ś", "s").replace("ą", "a").replace("ę", "e").replace("-", "")
        city_data = CITIES.get(clean_key, CITIES["bielsko"])
        
        url = f"https://api.open-meteo.com/v1/forecast?latitude={city_data['lat']}&longitude={city_data['lon']}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Europe%2FWarsaw"

        try:
            async with self.bot.session.get(url) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                daily = data['daily']
                prob = daily['precipitation_probability_max'][0]
                
                if prob > 50:
                    advice, color = "**Będzie dzisiaj padać**", discord.Color.red()
                elif prob > 15:
                    advice, color = "**Może pokropić**", discord.Color.gold()
                else:
                    advice, color = "**Niebo jest czyste**", discord.Color.green()

                embed = discord.Embed(
                    title=f"Prognoza: {city_data['name']}",
                    description=f"**{advice}**",
                    color=color,
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name="Max", value=f"{daily['temperature_2m_max'][0]}°C", inline=True)
                embed.add_field(name="Min", value=f"{daily['temperature_2m_min'][0]}°C", inline=True)
                embed.add_field(name="Opady", value=f"{prob}%", inline=True)

                chart_url = get_weather_chart_url(self.db_path)
                if chart_url:
                    embed.set_image(url=chart_url)

                embed.set_footer(text="Dane: Open-Meteo")
                return embed
        except Exception as e:
            logger.error(f"Błąd w get_forecast_embed: {e}")
            return None

    @commands.hybrid_command(name="prognoza", description="Sprawdzenie prognozy pogody")
    @app_commands.describe(miasto="Wybierz miasto")
    @app_commands.choices(miasto=[
        app_commands.Choice(name="Bielsko-Biała", value="bielsko"),
        app_commands.Choice(name="Warszawa", value="warszawa"),
        app_commands.Choice(name="Kraków", value="krakow"),
        app_commands.Choice(name="Wrocław", value="wroclaw"),
        app_commands.Choice(name="Katowice", value="katowice")
    ])
    async def prognoza(self, ctx, miasto: str = "bielsko"):
        await ctx.defer()
        embed = await self.get_forecast_embed(miasto)
        if embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send("Nie udało się pobrać prognozy.")

    @tasks.loop(hours=4)
    async def update_weather_loop(self):
        await fetch_and_save_weather(self.db_path,self.bot.session)

    @tasks.loop(time=target_time)
    async def daily_weather_report(self):
        await fetch_and_save_weather(self.db_path,self.bot.session)
        data = await get_latest_weather_from_db(self.db_path)
        embed=await self.get_forecast_embed('bielsko')
        if data:        
            embed_current = create_weather_embed(data)
            await send_system_alert(self.bot, embed_current)
        if embed:
            await send_system_alert(self.bot,embed)

    @commands.hybrid_command(name="pogoda",description="Pokazuje pogode")
    async def pogoda(self, ctx):
        """Pokazuje obecną pogodę"""
        data = await get_latest_weather_from_db(self.db_path)
        if data:
            embed = create_weather_embed(data)
            chart_url=get_weather_chart_url(self.db_path)
            if chart_url:
                embed.set_image(url=chart_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Nie ma obecnie dostępu do danych pogodowych.")

async def setup(bot):
    await bot.add_cog(Weather(bot))