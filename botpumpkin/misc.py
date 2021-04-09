"""Provides a Discord bot cog containing a collection of simple miscellanous commands."""
import logging
import random

# Third party imports
import discord
from discord.ext import commands

# First party imports
import botpumpkin.discord.context as context_util
import botpumpkin.discord.message as message_util
import botpumpkin.discord.error as error_util
from botpumpkin.config import config


_log: logging.Logger = logging.getLogger(__name__)


# *** Misc ******************************************************************

class Misc(commands.Cog):
    """Command cog containing a collection of simple miscellanous commands."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the Misc cog.

        Args:
            bot (commands.Bot): The bot the cog will be added to.
        """
        self._bot: commands.Bot = bot

    # *** slap ******************************************************************

    @commands.command()
    async def slap(self, context: commands.Context, member: discord.Member) -> None:
        """Print a message stating that the bot has slapped the specified user, with a small chance to slap another random user instead.

        Args:
            context (commands.Context): The context of the command.
            member (discord.Member): The member to be slapped.
        """
        slap_random_chance: int = config["misc"]["slap-random-chance"] * 100
        if random.randint(1, slap_random_chance) == slap_random_chance:
            random_member: discord.Member = random.choice(context_util.get_channel(context).members)
            await message_util.send_simple_embed(context, f"{self._bot.user.mention} slapped {random_member.mention} instead!")
        else:
            await message_util.send_simple_embed(context, f"{self._bot.user.mention} slapped {member.mention}!")

    @slap.error
    async def slap_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        """Error handler for the slap command, which prints an alternative slap message for simple command errors.

        Args:
            context (commands.Context): The context of the command.
            exception (commands.CommandError): The exception which was thrown by the command.
        """
        if isinstance(exception, commands.BadArgument):
            await message_util.send_simple_embed(context, f"{self._bot.user.mention} didn't know who to slap, so {context.author.mention} was slapped instead!")
        elif isinstance(exception, commands.MissingRequiredArgument):
            await message_util.send_simple_embed(context, f"{self._bot.user.mention} slapped {context.author.mention}!")
        else:
            await error_util.log_command_error(_log, self._bot, context, exception)
