"""A collection of utility functions for performing typing and error checking on discord.ext.commands.Context objects."""
from typing import List, Optional, Union

# Third party imports
import discord
from discord.ext import commands

# First party imports
import botpumpkin.discord.guild as guild_util


# *** get_guild *************************************************************

def get_guild(context: commands.Context) -> discord.Guild:
    """Return the guild from the given context.

    Args:
        context (commands.Context): The context to return the guild from.

    Raises:
        ValueError: Raised if the context contains no guild.

    Returns:
        discord.Guild: The guild from the given context.
    """
    guild: Optional[discord.Guild] = context.guild
    if guild is None:
        raise ValueError("context.guild has no value")
    return guild


# *** get_guild_channels ****************************************************

def get_guild_channels(context: commands.Context) -> List[Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.StoreChannel]]:
    """Return a list of all channels from the given context.

    Args:
        context (commands.Context): The context to return all channels from.

    Raises:
        ValueError: Raised if the guild from the given context has no list of channels.

    Returns:
        List[Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.StoreChannel]]: The list of channels from the given context.
    """
    channels: List[Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.StoreChannel]] = get_guild(context).channels
    if channels is None:
        raise ValueError("context.guild.channels has no value")
    return channels


# *** get_channel ***********************************************************

def get_channel(context: commands.Context) -> discord.TextChannel:
    """Return the channel from the given context.

    Args:
        context (commands.Context): The context to return the channel from.

    Raises:
        ValueError: Raised if the channel is not a TextChannel, which means the channel is not from a guild.

    Returns:
        discord.TextChannel: The channel from the given context.
    """
    channel: Union[discord.TextChannel, discord.DMChannel, discord.GroupChannel] = context.channel
    if not isinstance(channel, discord.TextChannel):
        raise ValueError("Channel is not from guild")
    return channel


# *** get_channel_by_name ***************************************************

def get_channel_by_name(context: commands.Context, channel_name: str) -> discord.TextChannel:
    """Return the channel from the list of channels in the given context that has the given name.

    Args:
        context (commands.Context): The context to return the channel from.
        channel_name (int): The name of the channel to return.

    Returns:
        discord.TextChannel: The channel with the given name from the given context.
    """
    return guild_util.get_channel_by_name(get_guild(context), channel_name)


# *** get_author ************************************************************

def get_author(context: commands.Context) -> discord.Member:
    """Return the member who sent the message for the given context.

    Args:
        context (commands.Context): The context to return the author from.

    Returns:
        discord.Member: The author for the given context.
    """
    author: Union[discord.User, discord.Member] = context.author
    if not isinstance(author, discord.Member):
        raise ValueError("Author is not from guild")
    return author
