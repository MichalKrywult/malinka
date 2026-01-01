import datetime

from discord.ext import commands, tasks
from utils.notifer import send_system_alert
from utils.weather_handler import (
    create_weather_embed,
    fetch_and_save_weather,
    get_latest_weather_from_db,
)

target_time = datetime.time(hour=5, minute=15)

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = bot.config['DB_PATH']
        self.daily_weather_report.start()
        self.update_weather_loop.start()

    @tasks.loop(hours=4)
    async def update_weather_loop(self):
        await fetch_and_save_weather(self.db_path,self.bot.session)

    @tasks.loop(time=target_time)
    async def daily_weather_report(self):
        await fetch_and_save_weather(self.db_path,self.bot.session)
        data = await get_latest_weather_from_db(self.db_path)
        
        if data:
            embed = create_weather_embed(data)             
            await send_system_alert(self.bot,embed)

    @commands.hybrid_command(name="pogoda")
    async def pogoda(self, ctx):
        """Pokazuje obecną pogodę"""
        data = await get_latest_weather_from_db(self.db_path)
        if data:
            embed = create_weather_embed(data)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Nie ma obecnie dostępu do danych pogodowych.")
async def setup(bot):
    await bot.add_cog(Weather(bot))