import discord
from discord.ext import commands

from config import config

class Help(commands.Cog):
    """Contains a group of help commands for displaying the commands supported by this and other bots"""
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    @commands.guild_only()
    async def help(self, ctx: commands.Context) -> None:
        """Prints information on the current commands supported by BotPumpkin"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(description = "BotPumpkin is a custom bot for starting and stopping our game server, and for doing some other fun and useful things.", color = int(config["color"], 0))
            embed.add_field(name = "`.slap`", value = "Let BotPumpkin teach someone else a lesson", inline = False)
            embed.add_field(name = "`.server start`", value = "Starts our game server", inline = False)
            embed.add_field(name = "`.server stop`", value = "Stops our game server", inline = False)
            embed.add_field(name = "`.help Groovy`", value = "Displays commonly used commands for Groovy", inline = False)
            embed.add_field(name = "`.help sesh`", value = "Displays commonly used commands for sesh", inline = False)
            embed.set_author(name = self.bot.user.name, icon_url = self.bot.user.avatar_url)
            await ctx.send(embed = embed)

    @help.command(name = "groovy")
    @commands.guild_only()
    async def help_groovy(self, ctx: commands.Context) -> None:
        """Prints a selection of useful commands which are supported by the Groovy Discord bot"""
        groovy = None
        for user in self.bot.users:
            if user.name == "Groovy":
                groovy = user
                break

        embed = discord.Embed(description = f"Groovy is a bot for playing music in the voice channels. See [here](https://groovy.bot/commands?prefix=-) for a full list of commands.", color = int(config["color"], 0))
        embed.add_field(name = "`-play [search_query]`", value = "Adds the song to the queue, and starts playing it if nothing is playing", inline = False)
        embed.add_field(name = "`-play`", value = "Starts playing the queue", inline = False)
        embed.add_field(name = "`-pause`", value = "Pauses the current song (saves the position in the song)", inline = False)
        embed.add_field(name = "`-stop`", value = "Stops the current song (doesn't save the position in the song", inline = False)
        embed.add_field(name = "`-next`", value = "Skips to the next song", inline = False)
        embed.add_field(name = "`-back`", value = "Skips to the previous song", inline = False)
        embed.add_field(name = "`-queue`", value = "Displays the queue contents", inline = False)
        embed.add_field(name = "`-clear`", value = "Empties the queue", inline = False)
        embed.add_field(name = "`-jump [track_position]`", value = "Jumps to a specific point in the queue", inline = False)
        embed.add_field(name = "`-shuffle`", value = "Shuffles the queue", inline = False)
        embed.add_field(name = "`-move [track_position], [new_position]`", value = "Moves a song from one position to another in the queue", inline = False)
        embed.add_field(name = "`-saved queues`", value = "Displays your saved queues", inline = False)
        embed.add_field(name = "`-saved queues create [queue_name]`", value = "Creates the current queue as a new saved queue", inline = False)
        embed.add_field(name = "`-saved queues load [queue_name]`", value = "Loads all the songs from a saved queue into the current queue", inline = False)
        embed.add_field(name = "`-saved queues delete [queue_name]`", value = "Deletes a saved queue", inline = False)
        if groovy != None:
            embed.set_author(name = groovy.name, icon_url = groovy.avatar_url)
        else:
            embed.set_author(name = "Groovy")
        await ctx.send(embed = embed)

    @help.command(name = "sesh")
    @commands.guild_only()
    async def help_sesh(self, ctx: commands.Context) -> None:
        """Prints a selection of useful commands which are supported by the sesh Discord bot"""
        sesh = None
        for user in self.bot.users:
            if user.name == "sesh":
                sesh = user
                break

        embed = discord.Embed(description = f"sesh is a bot for planning hangouts and running polls. See [here](https://sesh.fyi/manual/) for a full list of commands.", color = int(config["color"], 0))
        embed.add_field(name = "`!create [event_description] [time_description]`", value = "Creates a new event with the given event description at the given time", inline = False)
        embed.add_field(name = "`!poll [poll_name] [poll_options]`", value = "Creates a new poll with the given name and options", inline = False)
        embed.add_field(name = "`!list`", value = "Lists all future scheduled events", inline = False)
        embed.add_field(name = "`!delete`", value = "Allows you to select an event to delete", inline = False)
        embed.add_field(name = "`!delete [search_query]`", value = "Searches for an event with a matching name and confirms whether to delete it", inline = False)
        if sesh != None:
            embed.set_author(name = sesh.name, icon_url = sesh.avatar_url)
        else:
            embed.set_author(name = "sesh")
        await ctx.send(embed = embed)