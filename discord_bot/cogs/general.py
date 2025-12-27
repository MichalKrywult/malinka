import random

import discord
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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