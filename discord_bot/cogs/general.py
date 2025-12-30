import os
import random
import time

import discord
import psutil
from discord.ext import commands, tasks
from utils.telegram_notifier import send_telegram_msg


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cpu_usage = 0
        self.memory_percent = 0
        self.temperature = 0
        self.alert_sent = False
        self.start_time = time.time()
        
        self.stats_monitor.start()
    
    def cog_unload(self):
        self.stats_monitor.cancel()

    @tasks.loop(seconds=30.0)
    async def stats_monitor(self):

        self.cpu_usage = psutil.cpu_percent(interval=None)
        self.memory_percent = psutil.virtual_memory().percent
        
        try:
            func = getattr(psutil, "sensors_temperatures", None)
            if func:
                data = func()
                if 'cpu_thermal' in data:
                    self.temperature = data['cpu_thermal'][0].current
                else:
                    self.temperature = "N/A"
            else:
                self.temperature = "N/A"
        except Exception as e:
            self.temperature = f"Błąd: {e}"

        if isinstance(self.temperature, (int, float)):

            if self.temperature > 70 and not self.alert_sent:
                await self.send_system_alert(f"**Alert Malinki!** Temp: {self.temperature}°C. Spowalnienie monitoringu.")
                self.alert_sent = True
                self.stats_monitor.change_interval(seconds=180.0) #type: ignore
            
            elif self.temperature < 60 and self.alert_sent:
                await self.send_system_alert("**System schłodzony.** Powrót do standardowego monitoringu.")
                self.alert_sent = False
                self.stats_monitor.change_interval(seconds=30.0)

    async def send_system_alert(self, message):
        """Pomocnicza funkcja do wysyłania powiadomień"""
        owner_id = os.getenv('OWNER_DISCORD_ID')
        if owner_id:
            user = self.bot.get_user(int(owner_id)) or await self.bot.fetch_user(int(owner_id))
            if user:
                try:
                    await user.send(message)
                    await send_telegram_msg(message)
                except Exception as e:
                    print(f"Błąd wysyłania alertu: {e}")

    @commands.hybrid_command(name="stats", description="Pokazuje statystyki zdalnego serwera")
    async def stats(self, ctx):
        """
        Pokazuje statystyki zdalnego serwera
        """
        uptime_seconds = int(time.time() - self.start_time)
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        uptime_str = f"{days}d {hours}h {minutes}m"

        embed = discord.Embed(title=" Statystyki ", color=discord.Color.blue())
        embed.add_field(name="CPU", value=f"{self.cpu_usage}%", inline=True)
        embed.add_field(name="RAM", value=f"{self.memory_percent}%", inline=True)
        
        temp_val = f"{round(self.temperature, 1)}°C" if isinstance(self.temperature, (int, float)) else self.temperature
        embed.add_field(name="Temperatura", value=temp_val, inline=True)
        
        embed.set_footer(text=f"Uptime: {uptime_str} | Odświeżanie: {self.stats_monitor.seconds}s")
        await ctx.send(embed=embed)


    @commands.command()
    async def kostka(self, ctx):
        """Rzut kostką K6"""
        wynik = random.randint(1, 6)
        color = discord.Color.green() if wynik % 2 == 0 else discord.Color.red()
        
        embed = discord.Embed(
            title="Rzut kostką K6",
            description=f"Wyrzuciłeś: **{wynik}**",
            color=color
        )
        embed.set_footer(text=f"Wywołane przez {ctx.author.name}")
        await ctx.send(embed=embed)

    @commands.command()
    async def awatar(self, ctx, member: discord.Member | None=None):
        user = member or ctx.author
        embed = discord.Embed(title=f"Awatar użytkownika {user}", color=discord.Color.blurple())
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="help")
    async def help(self, ctx):
        """Wyświetla listę dostępnych komend"""
        embed = discord.Embed(
            title="Pomoc bota",
            description="Oto lista dostępnych komend i ich opisy:",
            color=discord.Color.gold()
        )
        # Iteruje przez wszystkie załadowane cogi
        for name, cog in self.bot.cogs.items():
            commands_list = ""
            for command in cog.get_commands():
                # Pomijamy komendy ukryte
                if command.hidden:
                    continue
                
                # Pobiera docstring (opis) lub daje tekst domyślny
                description = command.help or "Brak opisu"
                commands_list += f"`!{command.name}` - {description}\n"
            
            if commands_list:
                embed.add_field(name=f"Kategoria: {name}", value=commands_list, inline=False)

        await ctx.send(embed=embed)



async def setup(bot):
    await bot.add_cog(General(bot))







