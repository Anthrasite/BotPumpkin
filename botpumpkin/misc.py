import random

import discord
from discord.ext import commands

from util import *

class Misc(commands.Cog):
    """Contains a variety of simple, random commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def slap(self, ctx: commands.Context, member: discord.Member) -> None:
        """Gets BotPumpkin to slap the specified user, with a small chance to slap another random user instead"""
        if random.randint(1, 40) == 40:
            await send_simple_embed(ctx, f"{self.bot.user.mention} slapped {random.choice(ctx.channel.members).mention} instead!")
        else:
            await send_simple_embed(ctx, f"{self.bot.user.mention} slapped {member.mention}!")

    @slap.error
    async def slap_error(self, ctx: commands.Context, error: discord.DiscordException) -> None:
        """If the specified user cannot be found, slap the user who asked instead"""
        if isinstance(error, commands.BadArgument):
            await send_simple_embed(ctx, f"{self.bot.user.mention} didn't know who to slap, so {ctx.author.mention} was slapped instead!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await send_simple_embed(ctx, f"{self.bot.user.mention} slapped {ctx.author.mention}!")
        else:
            raise error