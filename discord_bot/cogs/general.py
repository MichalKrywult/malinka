import random

import discord
import psutil
from discord.ext import commands, tasks


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cpu_usage=0
        self.memory_percent=0
        self.temperature=0
        self.stats_monitor.start()
    
    def cog_unload(self):
        self.stats_monitor.stop()
        return super().cog_unload()
    
    @tasks.loop(seconds=1.0)
    async def stats_monitor(self):
        self.cpu_usage=psutil.cpu_percent(interval=None)
        self.memory_percent=psutil.virtual_memory().percent
        try:
            func = getattr(psutil, "sensors_temperatures", None)
            if func:
                data=func()
                self.temperature= data['cpu_thermal'][0].current
            else:
                self.temperature="N/A"
        except Exception as e:
            self.temperature= f"Błąd: {e}"

    @commands.hybrid_command()
    async def stats(self,ctx):
        embed=discord.Embed(title="Statystyki",color=discord.Color.blue())
        embed.add_field(name="Procesor",value=f"{round(self.cpu_usage,1)}%",inline=True)
        embed.add_field(name="Pamięć",value=f"{round(self.memory_percent,1)}%",inline=True)
        temp_display = f"{round(self.temperature, 1)}°C" if isinstance(self.temperature, (int, float)) else self.temperature
        embed.add_field(name="Temperatura",value=temp_display,inline=True)
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







