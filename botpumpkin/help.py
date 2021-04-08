"""Provides a Discord bot cog containing a collection of simple help commands."""
from typing import Optional

# Third party imports
import discord
from discord.ext import commands

# First party imports
import botpumpkin.discord.message as message_util
from botpumpkin.config import config


# *** Help ******************************************************************

class Help(commands.Cog):
    """Command cog containing a simple collection of help commands.

    Attributes:
        bot (commands.Bot): The bot the cog will be added to.
    """

    def __init__(self, bot: commands.Bot):
        """Initialize the Help cog.

        Args:
            bot (commands.Bot): The bot the cog will be added to.
        """
        self.bot: commands.Bot = bot

    # *** help ******************************************************************

    @commands.group()
    async def help(self, context: commands.Context) -> None:
        """Print information on the current commands supported by the bot.

        Args:
            context (commands.Context): The context of the command.
        """
        if context.invoked_subcommand is None:
            description_text: str = "BotPumpkin is a custom bot for starting and stopping our game server, and for doing some other fun and useful things."
            embed: discord.Embed = discord.Embed(description = description_text, color = int(config["colors"]["default"], 0))
            message_util.add_field_to_embed(embed, "`.slap`", "Let BotPumpkin teach someone else a lesson")
            message_util.add_field_to_embed(embed, "`.server start`", "Starts our game server")
            message_util.add_field_to_embed(embed, "`.server stop`", "Stops our game server")
            message_util.add_field_to_embed(embed, "`.help Groovy`", "Displays commonly used commands for Groovy")
            message_util.add_field_to_embed(embed, "`.help sesh`", "Displays commonly used commands for sesh")
            embed.set_author(name = self.bot.user.name, icon_url = str(self.bot.user.avatar_url))
            await context.send(embed = embed)

    # *** help groovy ***********************************************************

    @help.command(name = "groovy")
    async def help_groovy(self, context: commands.Context) -> None:
        """Print a selection of useful commands which are supported by the Groovy Discord bot.

        Args:
            context (commands.Context): The context of the command.
        """
        groovy: Optional[discord.User] = None
        for user in self.bot.users:
            if user.name == "Groovy":
                groovy = user
                break

        embed_description: str = "Groovy is a bot for playing music in the voice channels. "\
            "See [here](https://groovy.bot/commands?prefix=-) for a full list of commands."
        embed: discord.Embed = discord.Embed(description = embed_description, color = int(config["colors"]["default"], 0))
        message_util.add_field_to_embed(embed, "`-play [query]`", "Adds the song to the queue, and starts playing it if nothing is playing")
        message_util.add_field_to_embed(embed, "`-play`", "Starts playing the queue")
        message_util.add_field_to_embed(embed, "`-pause`", "Pauses the current song (saves the position in the song)")
        message_util.add_field_to_embed(embed, "`-stop`", "Stops the current song (doesn't save the position in the song")
        message_util.add_field_to_embed(embed, "`-next`", "Skips to the next song")
        message_util.add_field_to_embed(embed, "`-back`", "Skips to the previous song")
        message_util.add_field_to_embed(embed, "`-queue`", "Displays the queue contents")
        message_util.add_field_to_embed(embed, "`-clear`", "Empties the queue")
        message_util.add_field_to_embed(embed, "`-jump [track_position]`", "Jumps to a specific point in the queue")
        message_util.add_field_to_embed(embed, "`-shuffle`", "Shuffles the queue")
        message_util.add_field_to_embed(embed, "`-move [track_position], [new_position]`", "Moves a song from one position to another in the queue")
        message_util.add_field_to_embed(embed, "`-saved queues`", "Displays your saved queues")
        message_util.add_field_to_embed(embed, "`-saved queues create [name]`", "Creates the current queue as a new saved queue")
        message_util.add_field_to_embed(embed, "`-saved queues load [name]`", "Loads all the songs from a saved queue into the current queue")
        message_util.add_field_to_embed(embed, "`-saved queues delete [name]`", "Deletes a saved queue")
        if groovy is not None:
            embed.set_author(name = groovy.name, icon_url = str(groovy.avatar_url))
        else:
            embed.set_author(name = "Groovy")
        await context.send(embed = embed)

    # *** help sesh *************************************************************

    @help.command(name = "sesh")
    async def help_sesh(self, context: commands.Context) -> None:
        """Print a selection of useful commands which are supported by the sesh Discord bot.

        Args:
            context (commands.Context): The context of the command.
        """
        sesh: Optional[discord.User] = None
        for user in self.bot.users:
            if user.name == "sesh":
                sesh = user
                break

        embed_description: str = "sesh is a bot for planning hangouts and running polls. "\
            "See [here](https://sesh.fyi/manual/) for a full list of commands."
        embed: discord.Embed = discord.Embed(description = embed_description, color = int(config["colors"]["default"], 0))
        message_util.add_field_to_embed(embed, "`!create [event] [time]`", "Creates a new event with the given event description at the given time")
        message_util.add_field_to_embed(embed, "`!poll [name] [options]`", "Creates a new poll with the given name and options")
        message_util.add_field_to_embed(embed, "`!list`", "Lists all future scheduled events")
        message_util.add_field_to_embed(embed, "`!delete`", "Allows you to select an event to delete")
        message_util.add_field_to_embed(embed, "`!delete [query]`", "Searches for an event with a matching name and confirms whether to delete it")
        if sesh is not None:
            embed.set_author(name = sesh.name, icon_url = str(sesh.avatar_url))
        else:
            embed.set_author(name = "sesh")
        await context.send(embed = embed)
