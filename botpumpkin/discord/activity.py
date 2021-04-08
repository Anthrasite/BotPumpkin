"""A collection of utility functions for performing typing and error checking on discord.ext.commands.Bot objects."""
from typing import Optional, Union

# Third party imports
import discord


# *** get_activity_name *****************************************************

def get_activity_name(activity: Union[discord.BaseActivity, discord.Spotify]) -> Optional[str]:
    """Return the name of the given activity.

    Args:
        activity (Union[discord.BaseActivity, discord.Spotify]): The activity to return the name of.

    Raises:
        ValueError: Raised if the given activity has no name.

    Returns:
        str: The name of the activity.
    """
    if not isinstance(activity, (discord.Spotify, discord.Activity, discord.CustomActivity)):
        raise ValueError("Activity has no name")
    return activity.name
