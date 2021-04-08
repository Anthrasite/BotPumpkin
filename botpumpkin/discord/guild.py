"""A collection of utility functions for performing typing and error checking on discord.Guild objects."""
from typing import Optional, Union

# Third party imports
import discord


# *** get_channel_by_name ***************************************************

def get_channel_by_name(guild: discord.Guild, channel_name: str) -> discord.TextChannel:
    """Return the channel with the given channel name from the given guild.

    Args:
        guild (discord.Guild): The guild to retrieve the channel from.
        channel_name (str): The name of the channel to retrieve.

    Raises:
        ValueError: Thrown if the channel is not a discord.TextChannel, which means it isn't from a discord.Guild.

    Returns:
        discord.TextChannel: The channel with the given name.
    """
    channel: Optional[Union[discord.TextChannel, discord.VoiceChannel, discord.StoreChannel, discord.CategoryChannel]] = discord.utils.get(guild.channels, name = channel_name)
    if not isinstance(channel, discord.TextChannel):
        raise ValueError("Channel is not text channel")
    return channel
