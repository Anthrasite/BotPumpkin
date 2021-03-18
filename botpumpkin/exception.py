import discord
from discord.ext import commands

class InvalidChannelError(discord.DiscordException):
    """Raised when a command is sent to an invalid channel"""
    def __init__(self, ctx: commands.Context):
        super().__init__(f"{ctx.command} is invalid in the {ctx.channel} channel")