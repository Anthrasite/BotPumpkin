"""Provides a Discord bot cog containing a collection of commands for interacting with a game server running on an AWS instance."""
import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

# Third party imports
import discord
import pytz
from discord.ext import commands

# First party imports
import botpumpkin.discord.activity as activity_util
import botpumpkin.discord.check as custom_checks
import botpumpkin.discord.context as context_util
import botpumpkin.discord.error as error_util
import botpumpkin.discord.message as message_util
from botpumpkin.aws.ec2 import InstanceDescription, InstanceManager, InstanceState
from botpumpkin.aws.ssm import CommandExceededAttempts, CommandExceededWaitTime, CommandInvocation, CommandStatus, InstanceCommandRunner
from botpumpkin.config import config

_log: logging.Logger = logging.getLogger(__name__)


# *** InvalidInstanceStateError *********************************************

class InvalidInstanceStateError(commands.CommandError):
    """Exception which is raised when an instance has a state that is unexpected for the current context."""

    def __init__(self, state: str) -> None:
        """Initialize an InvalidInstanceStateError exception, including the instance state in the error message.

        Args:
            state (str): The invalid state of the instance.
        """
        super().__init__(f"The instance had the unexpected state {state}")


# *** InstanceNotRunningError ***********************************************

class InstanceNotRunningError(commands.CommandError):
    """Exception which is raised when a request to perform an action on the instance is received, but the instance is not running."""

    def __init__(self) -> None:
        """Initialize an InstanceNotRunningError exception."""
        super().__init__("Unable to perform action as the instance is not running")


# *** InstanceChangeToCurrentStateError *************************************

class InstanceChangeToCurrentStateError(commands.CommandError):
    """Exception which is raised when a request to change the instance to it's current state is recieved."""

    def __init__(self) -> None:
        """Initialize an InstanceChangeToCurrentStateError exception."""
        super().__init__("The instance can't be started because it is already running")


# *** GameAlreadyRunningError ***********************************************

class GameAlreadyRunningError(commands.CommandError):
    """Exception which is raised when a request to change the game running on the instance to the currently running game is recieved.

    Attributes:
        requested_game (str): The requested game which was already running.
    """

    def __init__(self, requested_game: str) -> None:
        """Initialize a GameAlreadyRunningError exception, including the requested game to the error message.

        Args:
            requested_game (str): The requested game which was already running.
        """
        self.requested_game: str = requested_game
        super().__init__(f"The game {requested_game} can't be started on the instance because it is already running")


# *** InvalidGameError ******************************************************

class InvalidGameError(commands.CommandError):
    """Exception which is raised when the configuration for a requested game couldn't be found.

    Attributes:
        requested_game (str): The invalid game.
    """

    def __init__(self, requested_game: str) -> None:
        """Initialize an InvalidGameError exception, including the requested game to the error message.

        Args:
            requested_game (str): The invalid game.
        """
        self.requested_game: str = requested_game
        super().__init__(f"No configuration was found for the requested game {requested_game}")


# *** ServerMaintenanceInProgress *******************************************

class ServerMaintenanceInProgress(commands.CommandError):
    """Exception which is raised when a server command is recieved while server maintenance is ongoing."""

    def __init__(self) -> None:
        """Initialize an ServerMaintenanceInProgress exception."""
        super().__init__("Unable to perform action as the instance is undergoing maintenance")


# *** Server ****************************************************************

class Server(commands.Cog):
    """Command cog containing commands for managing a game server run on an AWS instance.

    Attributes:
        bot (commands.Bot): The bot the cog will be added to.
        instance_lock (asyncio.Lock): A lock which controls access to the state of the AWS instance.
        self.instance_description (Optional[InstanceDescription]): The most recent description of the AWS instance.
        self.current_game (Optional[str]): The game server that is currently running on the AWS instance, if any.
        self.stop_reminder_sent (bool): Whether a reminder has been sent to stop the game server or not.
    """

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the Server cog, setting up the necessary parameters.

        Args:
            bot (commands.Bot): The bot the cog will be added to.
        """
        self._instance_id: str = os.environ["INSTANCE_ID"]
        self._aws_access_key_id: str = os.environ["ACCESS_KEY"]
        self._aws_secret_access_key: str = os.environ["SECRET_KEY"]
        self._region_name: str = os.environ["EC2_REGION"]

        self.bot: commands.Bot = bot
        self.instance_lock: asyncio.Lock = asyncio.Lock()
        self.instance_description: Optional[InstanceDescription] = None
        self.current_game: Optional[str] = None
        self.stop_reminder_sent: bool = False
        self.maintenance: bool = False

    # *** server ****************************************************************

    @commands.group()
    async def server(self, context: commands.Context) -> None:
        """Define the server command group, but do nothing.

        Args:
            context (commands.Context): The context of the command.
        """

    # *** server start **********************************************************

    @server.command(name = "start")
    @commands.has_any_role(config["server"]["admin-command-role"], config["server"]["user-command-role"])
    @custom_checks.is_channel(config["server"]["command-channel"])
    @commands.max_concurrency(1)
    async def server_start(self, context: commands.Context, *, game: str) -> None:
        """Attempt to start the AWS instance, wait for it to start, start the game server on the instance, and wait for the game server to start.

        Args:
            context (commands.Context): The context of the command.
            game (str): The game to start on the server.

        Raises:
            InvalidGameError: Raised when no configuration is found for the game requested.
            InstanceChangeToCurrentStateError: Raised when this command is called when the instance is already running.
            InvalidInstanceStateError: Raised when the instance has an unexpected state.
        """
        self._check_no_maintenance()
        self._check_valid_game(game)

        async with self.instance_lock:
            instance_manager: InstanceManager = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)
            self.instance_description = instance_manager.get_instance_description()
            _log.info(self.instance_description)

            # Error handling for invalid states when starting the server
            if self.instance_description.state == InstanceState.RUNNING:
                if self.current_game is None:
                    await self._warn_instance_running_without_game()
                raise InstanceChangeToCurrentStateError()
            if self.instance_description.state != InstanceState.STOPPED:
                raise InvalidInstanceStateError(self.instance_description.state.value)

            # Send a message indicating the server is starting
            progress_message: discord.Message = await message_util.send_simple_embed(context, "Starting the server...")

            # Start the instance
            self.instance_description = await instance_manager.start_instance()
            _log.info(self.instance_description)

            # Start the requested game
            instance_command_runner: InstanceCommandRunner = InstanceCommandRunner(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)
            command_invocation: CommandInvocation = await instance_command_runner.run_commands(config['server']['games'][game]['commands']['start'])
            _log.info(command_invocation)

            # Indicate that no reminder to stop the server has been sent
            self.stop_reminder_sent = False

            # Save the currently running game and update the bot activity
            await self._set_current_game(game)

            # Attempt to reach the game server,
            progress_message_text: str = "The server is now running. Connect to "\
                f"`{self.instance_description.public_ip_address}:{config['server']['games'][game]['port']}` to join the fun!"
            try:
                command_invocation = await instance_command_runner.run_commands_until_success(config['server']['games'][game]['commands']['ping'])
                _log.info(command_invocation)
            except (CommandExceededAttempts, CommandExceededWaitTime):
                progress_message_text = "The server is now running, but the game was unable to be reached, so something may have gone "\
                    f"wrong. Try connecting to `{self.instance_description.public_ip_address}:{config['server']['games'][game]['port']}` and contact "\
                    "an admin if you're unable to connect."

            # Delete the progress message and send a confirmation message
            await progress_message.delete()
            await message_util.send_simple_embed(context, progress_message_text)

    @server_start.error
    async def server_start_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        """Error handler for the server start command, which prints an error message based on the error raised.

        Args:
            context (commands.Context): The context of the command.
            exception (commands.CommandError): The exception which was thrown by the command.
        """
        if isinstance(exception, commands.MissingRequiredArgument):
            message_text = "You must specify which game you wish to start on the server.\n"\
                f"For example: `{self.bot.command_prefix}{context.command} {list(config['server']['games'].keys())[0]}`"
            await message_util.send_simple_embed(context, message_text)
        elif isinstance(exception, InvalidGameError):
            await message_util.send_simple_embed(context, f"The game _{exception.requested_game}_ isn't setup to run on the server.")
        elif isinstance(exception, InstanceChangeToCurrentStateError):
            await message_util.send_simple_embed(context, "The server is already running.")
        else:
            await self._log_command_error(context, exception)

    # *** server stop ***********************************************************

    @server.command(name = "stop")
    @commands.has_any_role(config["server"]["admin-command-role"], config["server"]["user-command-role"])
    @custom_checks.is_channel(config["server"]["command-channel"])
    @commands.max_concurrency(1)
    async def server_stop(self, context: commands.Context) -> None:
        """Attempt to stop the game server running on the instance, wait for it to stop, attempt to stop the AWS instance, and wait for it to stop.

        Args:
            context (commands.Context): The context of the command.

        Raises:
            InstanceChangeToCurrentStateError: Raised when this command is called when the instance is already stopped.
            InvalidInstanceStateError: Raised when the instance has an unexpected state.
        """
        self._check_no_maintenance()

        async with self.instance_lock:
            instance_manager: InstanceManager = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)
            self.instance_description = instance_manager.get_instance_description()
            _log.info(self.instance_description)

            # Error handling for invalid states when stopping the server
            if self.instance_description.state == InstanceState.STOPPED:
                raise InstanceChangeToCurrentStateError()
            if self.instance_description.state != InstanceState.RUNNING:
                raise InvalidInstanceStateError(self.instance_description.state.value)

            if self.current_game is None:
                await self._warn_instance_running_without_game()

            # Send a message indicating the server is stopping
            progress_message: discord.Message = await message_util.send_simple_embed(context, "Stopping the server...")

            # Stop the requested game
            if self.current_game is not None:
                instance_command_runner: InstanceCommandRunner = InstanceCommandRunner(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)
                command_invocation: CommandInvocation = await instance_command_runner.run_commands(config['server']['games'][self.current_game]['commands']['stop'])
                _log.info(command_invocation)

            # Stop the instance
            self.instance_description = await instance_manager.stop_instance()
            _log.info(self.instance_description)

            # Delete the progress message and send a confirmation message
            await progress_message.delete()
            await message_util.send_simple_embed(context, "The server has been stopped. Thanks for playing!")

            # Clear the current game and the bot activity
            await self._set_current_game(None)

    @server_stop.error
    async def server_stop_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        """Error handler for the server stop command, which prints an error message based on the error raised.

        Args:
            context (commands.Context): The context of the command.
            exception (commands.CommandError): The exception which was thrown by the command.
        """
        if isinstance(exception, InstanceChangeToCurrentStateError):
            await message_util.send_simple_embed(context, "The server is already stopped.")
        else:
            await self._log_command_error(context, exception)

    # *** server status *********************************************************

    @server.command(name = "status")
    @commands.has_any_role(config["server"]["admin-command-role"], config["server"]["user-command-role"])
    @custom_checks.is_channel_for_role(config["server"]["command-channel"], config["server"]["user-command-role"])
    @commands.max_concurrency(1)
    async def server_status(self, context: commands.Context) -> None:
        """Print the status of the AWS instance.

        Args:
            context (commands.Context): The context of the command.
        """
        admin_status = discord.utils.get(context_util.get_author(context).roles, name = config["server"]["admin-command-role"])
        if not admin_status:
            self._check_no_maintenance()

        async with self.instance_lock:
            instance_manager: InstanceManager = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)
            self.instance_description = instance_manager.get_instance_description()
            _log.info(self.instance_description)

            # Retrieve the current player count
            current_game: str = self.current_game if self.current_game is not None else "None"
            if self.current_game is not None:
                command_manager: InstanceCommandRunner = InstanceCommandRunner(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)
                invocation: CommandInvocation = await command_manager.run_commands(config['server']['games'][self.current_game]['commands']['query-player-count'])
                player_count: int = int(invocation.output) if invocation.status == CommandStatus.SUCCESS and invocation.output.isdigit() else 0

            if admin_status:
                # Get additional admin-only information, including the launch time and server ping
                state: str = f":{self._get_state_color()}_circle: {self.instance_description.state.value.capitalize()}"
                launch_time: datetime = self.instance_description.launch_time.astimezone(pytz.timezone(config['server']['default-timezone']))
                if self.current_game is not None:
                    invocation = await command_manager.run_commands(config['server']['games'][self.current_game]['commands']['ping'])
                    ping: str = invocation.output if invocation.status == CommandStatus.SUCCESS else "Connection failed"

                # Create and send the embed with user and admin-only information
                embed: discord.Embed = discord.Embed(title = f"Status of {self.instance_description.image_id}", color = int(config["colors"]["default"], 0))
                message_util.add_field_to_embed(embed, "State", state)
                if self.instance_description.state == InstanceState.RUNNING:
                    message_util.add_field_to_embed(embed, "Current game", f"{':warning: ' if self.current_game is None else ''}{current_game}")
                    if self.current_game is not None:
                        message_util.add_field_to_embed(embed, "Game server ping", ping)
                        message_util.add_field_to_embed(embed, "Current players", str(player_count))
                    message_util.add_field_to_embed(embed, "IP address", f"`{self.instance_description.public_ip_address}`")
                    message_util.add_field_to_embed(embed, "DNS name", f"`{self.instance_description.public_dns_name}`")
                message_util.add_field_to_embed(embed, "Last launch time", str(launch_time))
                await context.send(embed = embed)
            else:
                # Create and send the simple embed with user information
                message = f"The server is currently {self.instance_description.state.value.lower()}"
                if self.instance_description.state == InstanceState.RUNNING and self.current_game is not None:
                    message += f" the game {self.current_game} and there {'is' if player_count == 1 else 'are'} "\
                        f"{player_count} {'person' if player_count == 1 else 'people'} playing. Connect to "\
                        f"`{self.instance_description.public_ip_address}:{config['server']['games'][self.current_game]['port']}` to join the fun!"
                else:
                    message += "."
                await message_util.send_simple_embed(context, message)

    @server_status.error
    async def server_status_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        """Error handler for the server status command, which prints an error message based on the error raised.

        Args:
            context (commands.Context): The context of the command.
            exception (commands.CommandError): The exception which was thrown by the command.
        """
        await self._log_command_error(context, exception)

    # *** server change *********************************************************

    @server.command(name = "change")
    @commands.has_any_role(config["server"]["admin-command-role"], config["server"]["user-command-role"])
    @custom_checks.is_channel(config["server"]["command-channel"])
    @commands.max_concurrency(1)
    async def server_change(self, context: commands.Context, *, game: str) -> None:
        """Attempt to stop the game server running on the instance, wait for it to stop, start a different game on the instance, and wait for it to start.

        Args:
            context (commands.Context): The context of the command.
            game (str): The game to start on the AWS instance.

        Raises:
            InvalidGameError: Raised when no configuration is found for the game requested.
            GameAlreadyRunningError: Raised when the requested game is already running on the AWS instance.
            InstanceNotRunningError: Raised when the AWS instance isn't running.
        """
        self._check_no_maintenance()
        self._check_valid_game(game)
        self._check_game_not_running(game)

        async with self.instance_lock:
            instance_manager: InstanceManager = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)
            self.instance_description = instance_manager.get_instance_description()
            _log.info(self.instance_description)

            if self.instance_description.state != InstanceState.RUNNING:
                raise InstanceNotRunningError()
            if self.current_game is None:
                await self._warn_instance_running_without_game()

            # Send a message indicating the game running on the server is changing
            progress_message: discord.Message = await message_util.send_simple_embed(context, "Changing the game running on the server...")

            # Stop the current game and start the new game
            instance_command_runner: InstanceCommandRunner = InstanceCommandRunner(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)
            if self.current_game is not None:
                command_invocation: CommandInvocation = await instance_command_runner.run_commands(config['server']['games'][self.current_game]['commands']['stop'])
                _log.info(command_invocation)
            command_invocation = await instance_command_runner.run_commands(config['server']['games'][game]['commands']['start'])
            _log.info(command_invocation)

            # Reset the reminder to stop the server
            self.stop_reminder_sent = False

            # Save the currently running game and update the bot activity
            await self._set_current_game(game)

            # Attempt to reach the game server,
            progress_message_text: str = "The game running on the server has been changed. "\
                f"Connect to `{self.instance_description.public_ip_address}:{config['server']['games'][game]['port']}` to join the fun!"
            try:
                command_invocation = await instance_command_runner.run_commands_until_success(config['server']['games'][game]['commands']['ping'])
                _log.info(command_invocation)
            except (CommandExceededAttempts, CommandExceededWaitTime):
                progress_message_text = "The game running on the server has been changed, but was unable to be reached, so something may have gone "\
                    f"wrong. Try connecting to `{self.instance_description.public_ip_address}:{config['server']['games'][game]['port']}` and contact "\
                    "an admin if you're unable to connect."

            # Delete the progress message and send a confirmation message
            await progress_message.delete()
            await message_util.send_simple_embed(context, progress_message_text)

    @server_change.error
    async def server_change_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        """Error handler for the server change command, which prints an error message based on the error raised.

        Args:
            context (commands.Context): The context of the command.
            exception (commands.CommandError): The exception which was thrown by the command.
        """
        if isinstance(exception, commands.MissingRequiredArgument):
            message_text: str = "You must specify which game you wish to switch to.\n"\
                f"For example: `{self.bot.command_prefix}{context.command} {list(config['server']['games'].keys())[0]}`"
            await message_util.send_simple_embed(context, message_text)
        elif isinstance(exception, InvalidGameError):
            await message_util.send_simple_embed(context, f"The game _{exception.requested_game}_ isn't setup to run on the server.")
        elif isinstance(exception, InstanceNotRunningError):
            await message_util.send_simple_embed(context, "The game cannot be changed unless the server is running.")
        elif isinstance(exception, GameAlreadyRunningError):
            await message_util.send_simple_embed(context, f"The server is already running the game _{exception.requested_game}_.")
        else:
            await self._log_command_error(context, exception)

    # *** server disable ********************************************************

    @server.command(name = "disable")
    @commands.has_role(config["server"]["admin-command-role"])
    async def server_disable(self, context: commands.Context) -> None:
        """Disable server commands to allow maintenance to be performed on the instance without the bot attempting to change it's state.

        Args:
            context (commands.Context): The context of the command.
        """
        if self.maintenance:
            await message_util.send_simple_embed(context, "Server commands are already disabled for maintenance.")
        else:
            self.maintenance = True
            await message_util.send_simple_embed(context, "Server commands have been temporarily disabled to allow for server maintenance.")

    # *** server enable *********************************************************

    @server.command(name = "enable")
    @commands.has_role(config["server"]["admin-command-role"])
    async def server_enable(self, context: commands.Context) -> None:
        """Enable server commands after maintenance has been performed on the instance.

        Args:
            context (commands.Context): The context of the command.
        """
        if not self.maintenance:
            await message_util.send_simple_embed(context, "Server commands aren't currently disabled for maintenance.")
        else:
            self.maintenance = False
            await message_util.send_simple_embed(context, "Server maintenance has finished and the server is ready for games again!")

    @server_disable.error
    @server_enable.error
    async def server_maintenance_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        """Error handler for the server enable and disable commands, which prints an error message based on the error raised.

        Args:
            context (commands.Context): The context of the command.
            exception (commands.CommandError): The exception which was thrown by the command.
        """
        await self._log_command_error(context, exception)

    # *** on_member_update ******************************************************

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """When a member status is updated, if all users aren't playing the currently running game and the server is still running, send a reminder message.

        Args:
            before (discord.Member): The previous status of the member who's status changed.
            after (discord.Member): The current status of the member who's status changed.
        """
        # Attempt to avoid sending a notification if the server state is changing from a command or if the server is undergoing maintenance
        if not self.maintenance and not self.instance_lock.locked():
            # Get the instance description if it hasn't been set yet
            if self.instance_description is None:
                self.instance_description = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name).get_instance_description()
                _log.info(self.instance_description)

            # Only send a reminder if the server is actually running
            if self.instance_description.state == InstanceState.RUNNING:
                # Raise an error if the server is running and there is no current game
                if self.current_game is None:
                    await self._warn_instance_running_without_game()
                else:
                    # If the reminder has already been sent, check if anyone has started the game again, so the reminder can be resent
                    if self.stop_reminder_sent:
                        if (not any(activity_util.get_activity_name(activity) == self.current_game for activity in before.activities) and
                                any(activity_util.get_activity_name(activity) == self.current_game for activity in after.activities)):
                            self.stop_reminder_sent = False

                    # If the reminder hasn't been sent, ensure that someone just stopped playing the game and that no one else is playing it, and if so,
                    # send a reminder
                    else:
                        if (any(activity_util.get_activity_name(activity) == self.current_game for activity in before.activities) and
                                not any(activity_util.get_activity_name(activity) == self.current_game for activity in after.activities)):
                            anyone_playing_game: bool = False
                            for member in after.guild.members:
                                if not member.bot:
                                    for activity in member.activities:
                                        if activity_util.get_activity_name(activity) == self.current_game:
                                            anyone_playing_game = True

                            if not anyone_playing_game:
                                await message_util.send_simple_here_mention_to_channel(after.guild, config["server"]["command-channel"])
                                message_text: str = f"The server is running, but it looks like no one is playing {self.current_game} anymore. "\
                                    f"Please run `{self.bot.command_prefix}server stop` to stop the server if you're finished playing!"
                                await message_util.send_simple_embed_to_channel(after.guild, config["server"]["command-channel"], message_text)
                                self.stop_reminder_sent = True

    # *** _log_command_error ****************************************************

    async def _log_command_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        if isinstance(exception, ServerMaintenanceInProgress):
            await message_util.send_simple_embed(context, f"The command `{self.bot.command_prefix}{context.command}` Unable to stop the server as it is currently undergoing maintenance. Please try again later.")
        else:
            await error_util.log_command_error(_log, self.bot, context, exception)

    # *** _check_valid_game *****************************************************

    @staticmethod
    def _check_valid_game(game: str) -> None:
        if game not in config["server"]["games"]:
            raise InvalidGameError(game)

    # *** _check_no_maintenance *************************************************

    def _check_no_maintenance(self) -> None:
        if self.maintenance:
            raise ServerMaintenanceInProgress()

    # *** _check_game_not_running ***********************************************

    def _check_game_not_running(self, game: str) -> None:
        if game == self.current_game:
            raise GameAlreadyRunningError(game)

    # *** _warn_instance_running_without_game ***********************************

    async def _warn_instance_running_without_game(self) -> None:
        """Print a warning that the instance is running, but the current_game is None."""
        await error_util.log_warning(_log, self.bot, "Instance is running, but no game server is running on it")

    # *** _set_current_game *****************************************************

    async def _set_current_game(self, game: Optional[str]) -> None:
        """Set the current game of the instance, and update the status of the bot.

        Args:
            game (Optional[str]): The game running on the instance, or None if no game is running.

        Raises:
            InvalidGameError: Raised when no configuration is found for the game requested.
        """
        if game is not None and game not in config["server"]["games"]:
            raise InvalidGameError(game)

        self.current_game = game

        activity: Optional[discord.activity.Game] = discord.Game(game) if game else None
        await self.bot.change_presence(activity = activity)

    # *** _get_state_color ******************************************************

    def _get_state_color(self) -> str:
        """Return a string containing the emote colour for the current AWS instance state.

        Raises:
            ValueError: Raised if the instance description isn't set.

        Returns:
            str: The colour for the current state.
        """
        if self.instance_description is None:
            raise ValueError("Instance description has no value")

        if self.instance_description.state == InstanceState.RUNNING:
            return "green"
        if self.instance_description.state == InstanceState.STOPPED:
            return "red"
        if self.instance_description.state == InstanceState.PENDING:
            return "yellow"
        if self.instance_description.state == InstanceState.STOPPING:
            return "orange"

        return "black"
