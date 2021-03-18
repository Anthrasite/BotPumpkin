import logging
import os

import discord
from discord.ext import commands

from config import config
from help import Help
from server import Server
from misc import Misc

log = logging.getLogger()

class BotPumpkin(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.presences = True
        intents.members = True
        super().__init__(command_prefix = config["prefix"], case_insensitive = True, help_command = None, intents = intents)

        self.add_cog(Help(self))
        self.add_cog(Misc(self))
        self.add_cog(Server(self))

    async def on_ready(self) -> None:
        """Print a status message once the bot is initialized"""
        log.info(f"Logged in as {bot.user}")

bot = BotPumpkin()
bot.run(os.getenv("DISCORD_TOKEN"))