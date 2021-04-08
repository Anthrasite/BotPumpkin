"""A collection of utility functions for using and sending messages to Discord."""
from typing import Optional

# Third party imports
import discord
from discord.ext import commands

# First party imports
import botpumpkin.discord.bot as bot_util
import botpumpkin.discord.guild as guild_util
from botpumpkin.config import config


# *** send_simple_embed *****************************************************

async def send_simple_embed(context: commands.Context, message: str, color: str = config["colors"]["default"]) -> discord.Message:
    """Send a simple embed message using the given context, message, and an optional colour.

    Args:
        context (commands.Context): The context the embed will be sent in response to.
        message (str): The contents of the message.
        color (str, optional): The colour that will be used in the embed. Defaults to config["colors"]["default"].

    Returns:
        discord.Message: The embed message that was sent.
    """
    return await context.send(embed = discord.Embed(description = message, color = int(color, 0)))


# *** send_simple_embed_to_channel ******************************************

async def send_simple_embed_to_channel(guild: discord.Guild, channel_name: str, message: str, color: str = config["colors"]["default"]) -> discord.Message:
    """Send a simple embed message to the channel with the given name in the given guild, using the given message and an optional colour.

    Args:
        guild (discord.Guild): The guild containing the channel to send the message to.
        channel_name (int): The name of the channel to send the message to.
        message (str): The contents of the message
        color (str, optional): The colour that will be used in the embed. Defaults to config["colors"]["default"].

    Returns:
        discord.Message: The embed message that was sent.
    """
    channel: discord.TextChannel = guild_util.get_channel_by_name(guild, channel_name)
    return await channel.send(embed = discord.Embed(description = message, color = int(color, 0)))


# *** send_simple_embed_to_owner ********************************************

async def send_simple_embed_to_owner(bot: commands.Bot, message: str, title: str, color: str = config["colors"]["default"]) -> Optional[discord.Message]:
    """Send a simple embed message to the owner of the given bot (if the bot has an owner), using the given message and title, and an optional colour.

    Args:
        bot (commands.Bot): The bot to send the message from.
        message (str): The contents of the message.
        title (str): The title of the message.
        color (str, optional): The colour that will be used in the embed. Defaults to config["colors"]["default"].

    Returns:
        Optional[discord.Message]: The embed message that was sent, if a message was sent.
    """
    owner: Optional[discord.User] = bot_util.get_owner_if_set(bot)
    if owner is None:
        return None
    return await owner.send(embed = discord.Embed(title = title, description = message, color = int(color, 0)))


# *** add_field_to_embed ****************************************************

def add_field_to_embed(embed: discord.Embed, name: str, value: str) -> None:
    """Add an inline field with the given name and value to the given embed.

    Args:
        embed (discord.Embed): The embed to add the field to.
        name (str): The name of the field to add.
        value (str): The value of the field to add.
    """
    embed.add_field(name = name, value = value, inline = False)


# *** send_simple_here_mention_to_channel ***********************************

async def send_simple_here_mention_to_channel(guild: discord.Guild, channel_name: str) -> discord.Message:
    """Send a simple message containing only a @here mention to the channel with the given name in the given guild.

    Args:
        guild (discord.Guild): The guild containing the channel to send the message to.
        channel_name (int): The name of the channel to send the message to.

    Returns:
        discord.Message: The message that was sent.
    """
    channel: discord.TextChannel = guild_util.get_channel_by_name(guild, channel_name)
    return await channel.send("@here:")
