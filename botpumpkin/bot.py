"""A single BotPumpkin class which is used to start the bot."""
import logging
import traceback
from typing import Any

# Third party imports
import discord
from discord.ext import commands

# First party imports
import botpumpkin.discord.error as error_util
from botpumpkin.config import config
from botpumpkin.help import Help
from botpumpkin.misc import Misc
from botpumpkin.server import Server

_log: logging.Logger = logging.getLogger(__name__)


# *** BotPumpkin ************************************************************

class BotPumpkin(commands.Bot):
    """The base BotPumpkin bot, which adds cogs and sets up basic error handling."""

    def __init__(self) -> None:
        """Initialize the BotPumpkin bot by performing initial configuration and installing cogs."""
        intents: discord.Intents = discord.Intents.default()
        intents.presences = True
        intents.members = True
        super().__init__(command_prefix = config["prefix"], help_command = None, intents = intents, owner_id = config["owner-id"])

        self.add_check(_check_no_private_message)
        self._add_cogs()

    # *** on_ready **************************************************************

    async def on_ready(self) -> None:
        """Print a status message once the bot is initialized."""
        _log.info("Logged in as %s", self.user)

    # *** on_command_error ******************************************************

    async def on_command_error(self, context: commands.Context, exception: Exception) -> None:
        """Handle all command errors which aren't handled or are reraised by command error handlers.

        Args:
            context (commands.Context): The context of the command which caused the error.
            exception (Exception): The exception that was raised.
        """
        if not hasattr(context.command, 'on_error'):
            await error_util.log_command_error(_log, self, context, exception)

    # *** on_error **************************************************************

    async def on_error(self, event_method: str, *args: None, **kwargs: None) -> None:
        """Handle all non-command errors which aren't otherwise handled or are reraised.

        Args:
            event_method (str): The function that raised the error.
        """
        del args, kwargs

        error_message: str = f"Unhandled error in {event_method}"
        error_traceback: str = ''.join(traceback.format_exc())
        await error_util.log_error(_log, self, error_message, error_traceback)

    # *** _add_cogs *************************************************************

    def _add_cogs(self) -> None:
        """Add all enabled cogs to the bot."""
        self.add_cog(Help(self))
        if config.is_cog_enabled("misc"):
            self.add_cog(Misc(self))
        if config.is_cog_enabled("server"):
            self.add_cog(Server(self))


# *** _check_no_private_message *********************************************

def _check_no_private_message(context: commands.Context) -> Any:
    """Check if the given command context is for a private message.

    Args:
        context (commands.Context): The context of the command.

    Raises:
        commands.NoPrivateMessage: Raised if the command is a private message.

    Returns:
        Any: True if the command is not a private message.
    """
    if context.guild is None:
        raise commands.NoPrivateMessage()
    return True
