import logging

import discord
from discord.ext import commands

from config import config
from exception import InvalidChannelError

async def send_simple_embed(ctx: commands.Context,  message: str) -> discord.Message:
    """Sends a simple embed using the given message and the default colour"""
    return await ctx.send(embed = discord.Embed(description = message, color = int(config["color"], 0)))

async def send_simple_embed_to_channel(bot: commands.Bot, guild: discord.Guild, channel_name: str, message: str) -> discord.Message:
    """Send a simple embed to the channel with the given name in the given guild, using the given message and the default colour"""
    channel_id = discord.utils.get(guild.channels, name = channel_name).id
    channel = bot.get_channel(channel_id)
    return await channel.send(embed = discord.Embed(description = message, color = int(config["color"], 0)))

def verify_valid_channel(ctx: commands.Context, valid_channel: str) -> None:
    channel_id = discord.utils.get(ctx.guild.channels, name = valid_channel).id
    if ctx.channel.id is not channel_id:
        raise InvalidChannelError(ctx)