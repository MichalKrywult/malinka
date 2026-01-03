import asyncio
import logging
import socket
import time

import discord
import psutil
from discord.ext import commands, tasks
from utils.notifer import send_system_alert

logger = logging.getLogger('discord_bot')

class System(commands.Cog):
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager
        self.cpu_usage = 0
        self.memory_percent = 0
        self.temperature = 0
        self.alert_sent = False
        self.start_time = time.time()
        
        self.stats_monitor.start()
        self.daily_cleanup.start()
        
    
    def cog_unload(self):
        self.stats_monitor.cancel()
        self.daily_cleanup.cancel()

    def get_local_ip(self):
        """Pobiera lokalny adres IP."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    @tasks.loop(seconds=30.0)
    async def stats_monitor(self):
        self.cpu_usage = psutil.cpu_percent(interval=None)
        self.memory_percent = psutil.virtual_memory().percent
        

        try:
            func = getattr(psutil, "sensors_temperatures", None)
            if func:
                data = func()
                key = 'cpu_thermal' if 'cpu_thermal' in data else list(data.keys())[0] if data else None
                if key:
                    self.temperature = data[key][0].current
                else:
                    self.temperature = "N/A"
            else:
                self.temperature = "N/A"
        except Exception as e:
            self.temperature = f"Błąd: {e}"

        if isinstance(self.temperature, (int, float)):
            if self.temperature > 70 and not self.alert_sent:
                await send_system_alert(self.bot, f"**Alert Malinki!** Wysoka temperatura: {self.temperature}°C. Zwalniam monitoring.")
                self.alert_sent = True
                self.stats_monitor.change_interval(seconds=180.0)  #type: ignore
            
            elif self.temperature < 60 and self.alert_sent:
                await send_system_alert(self.bot, "**System schłodzony.** Powrót do normy.")
                self.alert_sent = False
                self.stats_monitor.change_interval(seconds=30.0)

        current_ip = self.get_local_ip()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'last_local_ip'")
            row = cursor.fetchone()
            last_ip = row[0] if row else None

            if current_ip != last_ip:
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                               ('last_local_ip', current_ip))
                conn.commit()
                await send_system_alert(self.bot, f"**Zmiana IP!** Nowy adres lokalny: `{current_ip}`")

    @commands.hybrid_command(name="stats", description="Pokazuje statystyki malinki")
    async def stats(self, ctx):
        """Pokazuje statystki malinki"""
        uptime_seconds = int(time.time() - self.start_time)
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        uptime_str = f"{days}d {hours}h {minutes}m"

        embed = discord.Embed(title="Statystyki systemowe", color=discord.Color.blue())
        embed.add_field(name="CPU", value=f"{self.cpu_usage}%", inline=True)
        embed.add_field(name="RAM", value=f"{self.memory_percent}%", inline=True)
        
        temp_val = f"{round(self.temperature, 1)}°C" if isinstance(self.temperature, (int, float)) else self.temperature
        embed.add_field(name="Temperatura", value=temp_val, inline=True)
                
        embed.set_footer(text=f"Uptime: {uptime_str} | Odświeżanie: {self.stats_monitor.seconds}s")
        await ctx.send(embed=embed)

    @tasks.loop(hours=24)
    async def daily_cleanup(self):
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(None, self.db.cleanup_old_data, 7)
        if stats:
            logger.info(f"Usunięto {stats['weather']} wpisów pogodowych. \n Usunięto {stats['reminders']}")

    

async def setup(bot):
    await bot.add_cog(System(bot, bot.db))