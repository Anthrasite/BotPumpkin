"""A collection of utility functions for error checking with objects from the discord.py library."""
import logging
import traceback
from typing import List

# Third party imports
from discord.ext import commands

# First party imports
import botpumpkin.discord.check as custom_checks
import botpumpkin.discord.message as message_util
from botpumpkin.config import config


# *** log_command_error *****************************************************

async def log_command_error(log: logging.Logger, bot: commands.Bot, context: commands.Context, exception: Exception) -> None:
    """Log the given command exception to the given logger and send a message to the owner of the given bot if the exception isn't a common exception to be ignored.

    Args:
        log (logging.Logger): The logger to log errors to.
        bot (commands.Bot): The bot to use to send error messages.
        context (commands.Context): The context of the command which raised the error.
        exception (Exception): The exception which was thrown.
    """
    if isinstance(exception, commands.MissingRole):
        await message_util.send_simple_embed(context, f"You must have the {exception.missing_role} role to run the `{bot.command_prefix}{context.command}` command.")
    elif isinstance(exception, commands.MissingAnyRole):
        await message_util.send_simple_embed(context, "You must have one of the following roles to run the "
                                             f"`{bot.command_prefix}{context.command}` command: {_join_missing_roles(exception)}")
    elif isinstance(exception, commands.MaxConcurrencyReached):
        await message_util.send_simple_embed(context, f"The `{bot.command_prefix}{context.command}` command is already running.")
    elif not isinstance(exception, (commands.NoPrivateMessage, commands.CommandNotFound, custom_checks.InvalidChannelError,
                                    custom_checks.InvalidChannelForRoleError)):
        await message_util.send_simple_embed(context, f"An unexpected error was encountered while trying to run `{bot.command_prefix}{context.command}`.")

        error_message: str = f"Unhandled error in `{bot.command_prefix}{context.command}`: {exception}"
        error_traceback: str = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        await log_error_message(log, bot, error_message, error_traceback)


# *** log_error *************************************************************

async def log_error(log: logging.Logger, bot: commands.Bot, exception: Exception) -> None:
    """Log the given exception to the given logger and send a message to the owner of the given bot.

    Args:
        log (logging.Logger): The logger to log errors to.
        bot (commands.Bot): The bot to use to send error messages.
        exception (Exception): The exception to log.
    """
    error_message: str = "Unhandled error"
    error_traceback: str = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    await log_error_message(log, bot, error_message, error_traceback)


# *** log_error_message *****************************************************

async def log_error_message(log: logging.Logger, bot: commands.Bot, error_message: str, error_traceback: str) -> None:
    """Log the given error message and stack trace to the given logger and send a message to the owner of the given bot.

    Args:
        log (logging.Logger): The logger to log errors to.
        bot (commands.Bot): The bot to use to send error messages.
        error_message (str): The description of the error.
        error_traceback (str): The stack trace of the error.
    """
    log.error(f"{error_message}\n{error_traceback}")

    embed_description: str = f"{error_message}\n```\n{error_traceback}\n```"
    if len(embed_description) > 2048:
        max_traceback_length: int = 2048 - (len(error_message) + 9) - 3
        embed_description = f"{error_message}\n```\n{error_traceback[:max_traceback_length]}...\n```"

    await message_util.send_simple_embed_to_owner(bot, embed_description, ":x: Error", config["colors"]["error"])


# *** log_warning ***********************************************************

async def log_warning(log: logging.Logger, bot: commands.Bot, warning_message: str) -> None:
    """Log the given warning message to the given logger and send a message to the owner of the given bot.

    Args:
        log (logging.Logger): The logger to log warnings to.
        bot (commands.Bot): The bot to use to send warning messages.
        warning_message (str): The description of the warning.
    """
    log.warning(warning_message)

    await message_util.send_simple_embed_to_owner(bot, warning_message, ":warning: Warning", config["colors"]["warning"])


# *** _join_missing_roles ***************************************************

def _join_missing_roles(exception: commands.MissingAnyRole) -> str:
    """Combine the set of roles contained in the commands.MissingAnyRole exception into a string.

    Args:
        exception (commands.MissingAnyRole): The MissingAnyRole exception to obtain the missing roles from.

    Returns:
        str: A string of comma-delimited missing roles.
    """
    roles: List[str] = []
    for role in exception.missing_roles:
        roles.append(str(role) if isinstance(role, int) else role)
    return ", ".join(roles)
