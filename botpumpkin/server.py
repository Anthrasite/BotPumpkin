import os
import asyncio
from enum import Enum
from datetime import datetime

import discord
from discord.ext import commands
import boto3
import pytz

from config import config
from util import *
from exception import InvalidChannelError

log = logging.getLogger(__name__)

class ServerCommandException(discord.DiscordException):
    """Base class for all exceptions thrown by commands in the server module"""
    pass

class NoInstanceDescriptionError(ServerCommandException):
    """Raised when no instance is returned from a request for instance descriptions from AWS"""
    def __init__(self) -> None:
        super().__init__("No instance descriptions returned")

class InvalidInstanceStateError(ServerCommandException):
    """Raised when no instance is returned from a request for instance descriptions from AWS"""
    def __init__(self, state: str) -> None:
        super().__init__(f"The instance had the unexpected state {state}")

class InstanceState(Enum):
    """The various valid states of an AWS instance"""
    PENDING = "pending"
    RUNNING = "running"
    SHUTTING_DOWN = "shutting-down"
    TERMINATED = "terminated"
    STOPPING = "stopping"
    STOPPED = "stopped"

class InstanceDescription:
    """Grabs the needed configuration information about an AWS instance from the JSON response from boto3.client.describe_instances function"""
    def __init__(self, instance_description: dict) -> None:
        if len(instance_description["Reservations"]) == 0 or len(instance_description["Reservations"][0]["Instances"]) == 0:
            raise NoInstanceDescriptionError()

        instance = instance_description["Reservations"][0]["Instances"][0]
        self.state = InstanceState(instance["State"]["Name"])
        self.image_id = instance["ImageId"]
        self.launch_time = instance["LaunchTime"]
        self.public_ip_address = instance["PublicIpAddress"] if "PublicIpAddress" in instance else ""
        self.public_dns_name = instance["PublicDnsName"] if "PublicDnsName" in instance else ""
        log.info(f"Instance {self.image_id} is currently in state {self.state.value}")

class InstanceManager:
    """Performs management of an AWS instance"""
    def __init__(self) -> None:
        """Initializes an AWS client connection"""
        self._client = boto3.client("ec2", aws_access_key_id = os.getenv("ACCESS_KEY"), aws_secret_access_key = os.getenv("SECRET_KEY"), region_name = os.getenv("EC2_REGION"))

    def get_instance_description(self) -> InstanceDescription:
        """Returns the description of an AWS instance with the configured instance id"""
        response = self._client.describe_instances(InstanceIds = [ os.getenv("INSTANCE_ID") ])
        return InstanceDescription(response)

    async def start_instance(self, curr_description: InstanceDescription) -> InstanceDescription:
        """Starts the instance with the configured instance id and queries it until it starts running"""
        self._client.start_instances(InstanceIds = [ os.getenv("INSTANCE_ID") ])
        return await self._query_instance(curr_description, InstanceState.RUNNING)

    async def stop_instance(self, curr_description: InstanceDescription) -> InstanceDescription:
        """Stops the instance with the configured instance id and queries it until it has stopped"""
        self._client.stop_instances(InstanceIds = [ os.getenv("INSTANCE_ID") ])
        return await self._query_instance(curr_description, InstanceState.STOPPED)

    async def _query_instance(self, curr_description: InstanceDescription, desired_state: InstanceState) -> InstanceDescription:
        """Queries the instance for it's current state, sleeping 3 seconds between queries, until the instance has the desired state"""
        valid_desired_states = [InstanceState.RUNNING, InstanceState.STOPPED]
        if desired_state not in valid_desired_states:
            raise ValueError("Invalid desired state in instance state query")

        while not (curr_description.state == desired_state):
            await asyncio.sleep(3)
            curr_description = self.get_instance_description()
            current_state = curr_description.state

            if current_state not in valid_desired_states and ((desired_state == InstanceState.RUNNING and current_state != InstanceState.PENDING) or (desired_state == InstanceState.STOPPED and current_state != InstanceState.STOPPING)):
                raise InvalidInstanceStateError(current_state.value)

        return curr_description

class Server(commands.Cog):
    """Contains a group of commands for managing a game server run on an AWS instance"""
    def __init__(self, bot):
        self.bot = bot
        self.instance_lock = asyncio.Lock()
        self.instance_description = None
        self.stop_reminder_sent = False

    @commands.group()
    @commands.guild_only()
    async def server(self, ctx: commands.Context) -> None:
        pass

    @server.command(name = "start")
    @commands.guild_only()
    @commands.max_concurrency(1)
    @commands.has_any_role(config["server"]["admin-command-role"], config["server"]["user-command-role"])
    async def server_start(self, ctx: commands.Context) -> None:
        """Starts the AWS instance"""
        await self._server_change_state(ctx, InstanceState.RUNNING)

    @server.command(name = "stop")
    @commands.guild_only()
    @commands.max_concurrency(1)
    @commands.has_any_role(config["server"]["admin-command-role"], config["server"]["user-command-role"])
    async def server_stop(self, ctx: commands.Context) -> None:
        """Stops the AWS instance"""
        await self._server_change_state(ctx, InstanceState.STOPPED)

    async def _server_change_state(self, ctx: commands.Context, desired_state: InstanceState) -> None:
        valid_desired_states = [InstanceState.RUNNING, InstanceState.STOPPED]
        if desired_state not in valid_desired_states:
            raise ValueError("Invalid desired state in instance state change")

        verify_valid_channel(ctx, config["server"]["command-channel"])

        async with self.instance_lock:
            # Get the instance
            instance_manager = InstanceManager()
            self.instance_description = instance_manager.get_instance_description()

            instance_state = self.instance_description.state
            state_past_tense = "started" if desired_state == InstanceState.RUNNING else "stopped"

            # Performs the correct action based on the desired state
            if instance_state == InstanceState.SHUTTING_DOWN or instance_state == InstanceState.TERMINATED:
                raise InvalidInstanceStateError(instance_state.value)
            elif desired_state == instance_state:
                await send_simple_embed(ctx, f"The {config['server']['current-game']} server is already {instance_state.value}.")
            elif (desired_state == InstanceState.RUNNING and instance_state == InstanceState.PENDING) or (desired_state == InstanceState.STOPPED and instance_state == InstanceState.STOPPING):
                await send_simple_embed(ctx, f"The {config['server']['current-game']} server is currently {instance_state.value} and will be {state_past_tense} shortly.")
            elif (desired_state == InstanceState.RUNNING and instance_state == InstanceState.STOPPING) or (desired_state == InstanceState.STOPPED and instance_state == InstanceState.PENDING):
                await send_simple_embed(ctx, f"The {config['server']['current-game']} server is currently {instance_state.value} and cannot be {state_past_tense}.")
            else:
                progress_message_text = f"{'Starting' if desired_state == InstanceState.RUNNING else 'Stopping'} the {config['server']['current-game']} server..."
                progress_message = None
                success_message_text = f"The {config['server']['current-game']} server is {desired_state.value}. "
                bot_activity = None

                # Send the progress message, saving it so it can later be deleted
                progress_message = await send_simple_embed(ctx, progress_message_text)

                if desired_state == InstanceState.RUNNING:
                    # Start the instance
                    self.instance_description = await instance_manager.start_instance(self.instance_description)

                    # Indicate that no reminder to stop the server has been sent
                    self.stop_reminder_sent = False

                    success_message_text += f"Connect to `{self.instance_description.public_ip_address}:{config['server']['server-port']}` to join the fun!"
                    bot_activity = discord.Game(config["server"]["current-game"])
                else:
                    # Stop the instance
                    self.instance_description = await instance_manager.stop_instance(self.instance_description)

                    success_message_text += f"Thanks for playing!"

                # Delete the progress message and send a confirmation message
                await progress_message.delete()
                await send_simple_embed(ctx, success_message_text)

                # Update the bot activity
                await self.bot.change_presence(activity = bot_activity)

    @server_start.error
    @server_stop.error
    async def server_change_state_error(self, ctx: commands.Context, error: discord.DiscordException) -> None:
        """If the user calling the command doesn't have the "Server Manager" role, inform them they need it"""
        if isinstance(error, commands.MissingAnyRole):
            await send_simple_embed(ctx, f"You must have one of the following roles to run this command: {', '.join(error.missing_roles)}")
        elif isinstance(error, commands.MaxConcurrencyReached):
            await send_simple_embed(ctx, f"Please wait until the previous server command finishes.")
        elif isinstance(error, InvalidInstanceStateError):
            await send_simple_embed(ctx, f"The server was unable to be started.")
        else:
            raise error

    @server.command(name = "status")
    @commands.guild_only()
    @commands.has_role(config["server"]["admin-command-role"])
    async def server_status(self, ctx: commands.Context) -> None:
        """Returns the status of the AWS instance"""
        async with self.instance_lock:
            instance_manager = InstanceManager()
            self.instance_description = instance_manager.get_instance_description()

            status_emote = f":{self._get_state_color(self.instance_description.state)}_circle:"

            embed = discord.Embed(title = f"Status of {self.instance_description.image_id}", color = int(config["color"], 0))
            embed.add_field(name = "State", value = f"{status_emote} {self.instance_description.state.value.capitalize()}", inline = False)
            embed.add_field(name = "Last launch time", value = f"{self.instance_description.launch_time.astimezone(pytz.timezone(config['server']['default-timezone']))}", inline = False)
            if self.instance_description.state == InstanceState.RUNNING:
                embed.add_field(name = "IP address", value = f"`{self.instance_description.public_ip_address}`", inline = False)
                embed.add_field(name = "DNS name", value = f"`{self.instance_description.public_dns_name}`", inline = False)

            await ctx.send(embed = embed)

    def _get_state_color(self, state: InstanceState) -> str:
        if self.instance_description.state == InstanceState.RUNNING:
            return "green"
        elif self.instance_description.state == InstanceState.STOPPED:
            return "red"
        elif self.instance_description.state == InstanceState.PENDING:
            return "yellow"
        elif self.instance_description.state == InstanceState.STOPPING:
            return "orange"
        else:
           return "black"

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """Send a reminder if all users aren't playing the current game and the server is still running"""
        if self.instance_description is None:
            self.instance_description = InstanceManager().get_instance_description()

        if self.instance_description.state == InstanceState.RUNNING:
            # If the reminder has already been sent, check if anyone has started the game again, so the reminder can be resent
            if self.stop_reminder_sent:
                if not any(activity.name == config["server"]["current-game"] for activity in before.activities) and any(activity.name == config["server"]["current-game"] for activity in after.activities):
                    self.stop_reminder_sent = False

            # If the reminder hasn't been sent, ensure that someone just stopped playing the game and that no one else is playing it, and if so, send a reminder
            else:
                if any(activity.name == config["server"]["current-game"] for activity in before.activities) and not any(activity.name == config["server"]["current-game"] for activity in after.activities):
                    anyone_playing_game = False
                    for member in after.guild.members:
                        if not member.bot:
                            for activity in member.activities:
                                if activity.name == config["server"]["current-game"]:
                                    anyone_playing_game = True

                    if not anyone_playing_game:
                        await send_simple_embed_to_channel(self.bot, after.guild, config["server"]["command-channel"], f"@here, the {config['server']['current-game']} server is running, but it looks like no one is playing {config['server']['current-game']} anymore. Please run `{config['prefix']}server stop` to stop the server if you're finished playing!")
                        self.stop_reminder_sent = True