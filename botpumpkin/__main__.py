"""Start BotPumpkin, a Discord bot with a variety of commands, including commands to interact with a game server setup on an AWS instance."""
import os

# Third party imports
import discord.ext.commands as commands

# First party imports
from botpumpkin.bot import BotPumpkin

bot: commands.Bot = BotPumpkin()
bot.run(os.environ["DISCORD_TOKEN"])
