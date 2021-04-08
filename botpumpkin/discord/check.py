"""A collection of check predicates for validating the state of a command from the discord.py library when called."""
from typing import Callable

# Third party imports
import discord
from discord.ext import commands

# First party imports
import botpumpkin.discord.context as context_util


# *** InvalidChannelError ***************************************************

class InvalidChannelError(commands.CheckFailure):
    """Exception which is raised when a command is sent to an invalid channel."""

    def __init__(self, context: commands.Context):
        """Initialize an InvalidChannelError exception using the context of the sent command.

        Args:
            context (commands.Context): The context of the command that was sent to an invalid channel.
        """
        super().__init__(f"{context.command} is invalid in the {context.channel} channel")


# *** InvalidChannelForRoleError ********************************************

class InvalidChannelForRoleError(commands.CheckFailure):
    """Exception which is raised when a command is sent to an invalid channel for a specific role."""

    def __init__(self, context: commands.Context, role_name: str):
        """Initialize an InvalidChannelError exception using the context of the sent command and the role of the command author.

        Args:
            context (commands.Context): The context of the command that was sent to an invalid channel.
            role (discord.Role): The role of the author of the command.
        """
        super().__init__(f"{context.command} is invalid in the {context.channel} channel for users with role {role_name}")


# *** is_channel ************************************************************

def is_channel(channel_name: str) -> Callable:
    """Check decorator to verify that a message is sent to the provided channel.

    Args:
        channel_name (str): The channel that the message must be sent to.

    Returns:
        Callable: The check decorator.
    """
    def check_valid_channel(context: commands.Context) -> bool:
        channel: discord.TextChannel = context_util.get_channel_by_name(context, channel_name)
        if context.channel.id is not channel.id:
            raise InvalidChannelError(context)
        return True

    predicate: Callable = check_valid_channel
    return commands.check(predicate)


# *** is_channel_for_role ***************************************************

def is_channel_for_role(channel_name: str, role_name: str) -> Callable:
    """Check decorator to verify that a message is sent to the provided channel if the author has the given role.

    Args:
        channel_name (str): The channel that the message must be sent to.
        role_name (str): The role the author must have.

    Returns:
        Callable: The check decorator.
    """
    def check_valid_channel_for_role(context: commands.Context) -> bool:
        if discord.utils.get(context_util.get_guild(context).roles, name = role_name) is None:
            raise ValueError("Role not found in guild")

        if discord.utils.get(context_util.get_author(context).roles, name = role_name) is None:
            return True

        channel: discord.TextChannel = context_util.get_channel_by_name(context, channel_name)
        if context.channel.id is not channel.id:
            raise InvalidChannelError(context)
        return True

    predicate: Callable = check_valid_channel_for_role
    return commands.check(predicate)
