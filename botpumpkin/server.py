"""Provides a Discord bot cog containing a collection of commands for interacting with a game server running on an AWS instance."""
import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

# Third party imports
import discord
import pytz
from discord.ext import commands, tasks

# First party imports
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
    """Command cog containing commands for managing a game server run on an AWS instance."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the Server cog, setting up the necessary parameters.

        Args:
            bot (commands.Bot): The bot the cog will be added to.
        """
        self._instance_id: str = os.environ["INSTANCE_ID"]
        self._aws_access_key_id: str = os.environ["ACCESS_KEY"]
        self._aws_secret_access_key: str = os.environ["SECRET_KEY"]
        self._region_name: str = os.environ["EC2_REGION"]

        self._bot: commands.Bot = bot
        self._instance_lock: asyncio.Lock = asyncio.Lock()
        self._current_game: Optional[str] = None
        self._maintenance: bool = False
        self._instance_query_no_players_count: int = -1

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
        async with self._instance_lock:
            self._check_no_maintenance()
            self._check_valid_game(game)

            instance_manager: InstanceManager = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key,
                                                                self._region_name)
            instance_description: InstanceDescription = instance_manager.get_instance_description()

            # Error handling for invalid states when starting the server
            if instance_description.state == InstanceState.RUNNING:
                if self._current_game is None:
                    await self._warn_instance_running_without_game()
                raise InstanceChangeToCurrentStateError()
            if instance_description.state != InstanceState.STOPPED:
                raise InvalidInstanceStateError(instance_description.state.value)

            # Send a message indicating the server is starting
            progress_message: discord.Message = await message_util.send_simple_embed(context, "Starting the server...")

            # Start the instance
            instance_description = await instance_manager.start_instance()

            # Start the requested game
            instance_command_runner: InstanceCommandRunner = InstanceCommandRunner(self._instance_id, self._aws_access_key_id,
                                                                                   self._aws_secret_access_key, self._region_name)
            await instance_command_runner.run_commands(config["server"]["games"][game]["commands"]["start"])

            # Save the currently running game and update the bot activity
            await self._set_current_game(game)

            # Attempt to reach the game server,
            progress_message_text: str = "The server is now running. Connect to "\
                f"`{instance_description.public_ip_address}:{config['server']['games'][game]['port']}` to join the fun!"
            try:
                await instance_command_runner.run_commands_until_success(config["server"]["games"][game]["commands"]["ping"])
            except (CommandExceededAttempts, CommandExceededWaitTime):
                progress_message_text = "The server is now running, but the game was unable to be reached, so something may have gone "\
                    f"wrong. Try connecting to `{instance_description.public_ip_address}:{config['server']['games'][game]['port']}` and contact "\
                    "an admin if you're unable to connect."

            # Delete the progress message and send a confirmation message
            await progress_message.delete()
            await message_util.send_simple_embed(context, progress_message_text)

            # Start the instance query loop
            self.query_instance_usage.start()

    @server_start.error
    async def server_start_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        """Error handler for the server start command, which prints an error message based on the error raised.

        Args:
            context (commands.Context): The context of the command.
            exception (commands.CommandError): The exception which was thrown by the command.
        """
        if isinstance(exception, commands.MissingRequiredArgument):
            message_text = "You must specify which game you wish to start on the server.\n"\
                f"For example: `{self._bot.command_prefix}{context.command} {list(config['server']['games'].keys())[0]}`"
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
        async with self._instance_lock:
            self._check_no_maintenance()

            instance_manager: InstanceManager = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key,
                                                                self._region_name)
            instance_description: InstanceDescription = instance_manager.get_instance_description()

            # Error handling for invalid states when stopping the server
            if instance_description.state == InstanceState.STOPPED:
                raise InstanceChangeToCurrentStateError()
            if instance_description.state != InstanceState.RUNNING:
                raise InvalidInstanceStateError(instance_description.state.value)

            if self._current_game is None:
                await self._warn_instance_running_without_game()

            # Stop the instance query loop
            self.query_instance_usage.cancel()

            # Send a message indicating the server is stopping
            progress_message: discord.Message = await message_util.send_simple_embed(context, "Stopping the server...")

            # Stop the current game
            if self._current_game is not None:
                await InstanceCommandRunner(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)\
                    .run_commands(config["server"]["games"][self._current_game]["commands"]["stop"])

            # Stop the instance
            await instance_manager.stop_instance()

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
            InvalidInstanceStateError: Raised when the instance has an unexpected state.
        """
        async with self._instance_lock:
            self._check_no_maintenance()
            self._check_valid_game(game)
            self._check_game_not_running(game)

            instance_description: InstanceDescription = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)\
                .get_instance_description()

            if instance_description.state != InstanceState.RUNNING:
                if instance_description.state == InstanceState.STOPPED:
                    raise InstanceNotRunningError()
                raise InvalidInstanceStateError(instance_description.state.value)
            if self._current_game is None:
                await self._warn_instance_running_without_game()

            # Stop the instance query loop
            self.query_instance_usage.cancel()

            # Send a message indicating the game running on the server is changing
            progress_message: discord.Message = await message_util.send_simple_embed(context, "Changing the game running on the server...")

            # Stop the current game and start the new game
            instance_command_runner: InstanceCommandRunner = InstanceCommandRunner(self._instance_id, self._aws_access_key_id,
                                                                                   self._aws_secret_access_key, self._region_name)
            if self._current_game is not None:
                await instance_command_runner.run_commands(config["server"]["games"][self._current_game]["commands"]["stop"])
            await instance_command_runner.run_commands(config["server"]["games"][game]["commands"]["start"])

            # Save the currently running game and update the bot activity
            await self._set_current_game(game)

            # Attempt to reach the game server,
            progress_message_text: str = "The game running on the server has been changed. "\
                f"Connect to `{instance_description.public_ip_address}:{config['server']['games'][game]['port']}` to join the fun!"
            try:
                await instance_command_runner.run_commands_until_success(config["server"]["games"][game]["commands"]["ping"])
            except (CommandExceededAttempts, CommandExceededWaitTime):
                progress_message_text = "The game running on the server has been changed, but was unable to be reached, so something may have gone "\
                    f"wrong. Try connecting to `{instance_description.public_ip_address}:{config['server']['games'][game]['port']}` and contact "\
                    "an admin if you're unable to connect."

            # Delete the progress message and send a confirmation message
            await progress_message.delete()
            await message_util.send_simple_embed(context, progress_message_text)

            # Start the instance query loop
            self.query_instance_usage.start()

    @server_change.error
    async def server_change_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        """Error handler for the server change command, which prints an error message based on the error raised.

        Args:
            context (commands.Context): The context of the command.
            exception (commands.CommandError): The exception which was thrown by the command.
        """
        if isinstance(exception, commands.MissingRequiredArgument):
            message_text: str = "You must specify which game you wish to switch to.\n"\
                f"For example: `{self._bot.command_prefix}{context.command} {list(config['server']['games'].keys())[0]}`"
            await message_util.send_simple_embed(context, message_text)
        elif isinstance(exception, InvalidGameError):
            await message_util.send_simple_embed(context, f"The game _{exception.requested_game}_ isn't setup to run on the server.")
        elif isinstance(exception, InstanceNotRunningError):
            await message_util.send_simple_embed(context, "The game cannot be changed unless the server is running.")
        elif isinstance(exception, GameAlreadyRunningError):
            await message_util.send_simple_embed(context, f"The server is already running the game _{exception.requested_game}_.")
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
        async with self._instance_lock:
            admin_status = discord.utils.get(context_util.get_author(context).roles, name = config["server"]["admin-command-role"])
            if not admin_status:
                self._check_no_maintenance()

            instance_description: InstanceDescription = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key, self._region_name)\
                .get_instance_description()

            # Retrieve the current player count
            current_game: str = self._current_game if self._current_game is not None else "None"
            if self._current_game is not None:
                instance_command_runner: InstanceCommandRunner = InstanceCommandRunner(self._instance_id, self._aws_access_key_id,
                                                                                       self._aws_secret_access_key, self._region_name)
                invocation: CommandInvocation = await instance_command_runner\
                    .run_commands(config["server"]["games"][self._current_game]["commands"]["query-player-count"])
                player_count: int = int(invocation.output) if invocation.status == CommandStatus.SUCCESS and invocation.output.isdigit() else 0

            if admin_status:
                # Get additional admin-only information, including the launch time and server ping
                state: str = f":{self._get_state_color(instance_description.state)}_circle: {instance_description.state.value.capitalize()}"
                launch_time: datetime = instance_description.launch_time.astimezone(pytz.timezone(config["server"]["default-timezone"]))
                if self._current_game is not None:
                    invocation = await instance_command_runner.run_commands(config["server"]["games"][self._current_game]["commands"]["ping"])
                    ping: str = invocation.output if invocation.status == CommandStatus.SUCCESS else "Connection failed"

                # Create and send the embed with user and admin-only information
                embed: discord.Embed = discord.Embed(title = f"Status of {instance_description.image_id}",
                                                     color = int(config["colors"]["default"], 0))
                message_util.add_field_to_embed(embed, "State", state)
                if instance_description.state == InstanceState.RUNNING:
                    message_util.add_field_to_embed(embed, "Current game", f"{':warning: ' if self._current_game is None else ''}{current_game}")
                    if self._current_game is not None:
                        message_util.add_field_to_embed(embed, "Game server ping", ping)
                        message_util.add_field_to_embed(embed, "Current players", str(player_count))
                    message_util.add_field_to_embed(embed, "IP address", f"`{instance_description.public_ip_address}`")
                    message_util.add_field_to_embed(embed, "DNS name", f"`{instance_description.public_dns_name}`")
                message_util.add_field_to_embed(embed, "Last launch time", str(launch_time))
                await context.send(embed = embed)
            else:
                # Create and send the simple embed with user information
                message = f"The server is currently {instance_description.state.value.lower()}"
                if instance_description.state == InstanceState.RUNNING and self._current_game is not None:
                    message += f" the game {self._current_game} and there {'is' if player_count == 1 else 'are'} "\
                        f"{player_count} {'person' if player_count == 1 else 'people'} playing. Connect to "\
                        f"`{instance_description.public_ip_address}:{config['server']['games'][self._current_game]['port']}` to join the fun!"
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

    # *** server disable ********************************************************

    @server.command(name = "disable")
    @commands.has_role(config["server"]["admin-command-role"])
    async def server_disable(self, context: commands.Context) -> None:
        """Disable server commands to allow maintenance to be performed on the instance without the bot attempting to change it's state.

        Args:
            context (commands.Context): The context of the command.
        """
        if self._maintenance:
            await message_util.send_simple_embed(context, "Server commands are already disabled for maintenance.")
        else:
            self._maintenance = True
            await message_util.send_simple_embed(context, "Server commands have been temporarily disabled to allow for server maintenance.")

    # *** server enable *********************************************************

    @server.command(name = "enable")
    @commands.has_role(config["server"]["admin-command-role"])
    async def server_enable(self, context: commands.Context) -> None:
        """Enable server commands after maintenance has been performed on the instance.

        Args:
            context (commands.Context): The context of the command.
        """
        if not self._maintenance:
            await message_util.send_simple_embed(context, "Server commands aren't currently disabled for maintenance.")
        else:
            self._maintenance = False
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

    # *** query_instance_usage **************************************************

    @tasks.loop(minutes = config["server"]["auto-shutdown-query-delay"])
    async def query_instance_usage(self) -> None:
        """Every three minutes, query the instance to determine if anyone is playing the current game, and shut down the server after 15 minutes if not.

        Raises:
            InvalidInstanceStateError: Raised when the instance has an unexpected state.
        """
        if self.query_instance_usage.current_loop == 0:
            self._instance_query_no_players_count = -1

        async with self._instance_lock:
            # Ensure maintenance isn't in progress
            if self._maintenance:
                await error_util.log_warning(_log, self._bot, "Instance query loop running while in maintenance mode")
                return

            # Get the instance description
            instance_manager: InstanceManager = InstanceManager(self._instance_id, self._aws_access_key_id, self._aws_secret_access_key,
                                                                self._region_name)
            instance_description: InstanceDescription = instance_manager.get_instance_description()

            # Ensure the instance is running and the current_game is set
            if instance_description.state != InstanceState.RUNNING:
                raise InvalidInstanceStateError(instance_description.state.value)
            if self._current_game is None:
                self._warn_instance_running_without_game()
                self.query_instance_usage.stop()
                return

            # Query for the number of players on the server currently
            instance_command_runner: InstanceCommandRunner = InstanceCommandRunner(self._instance_id, self._aws_access_key_id,
                                                                                   self._aws_secret_access_key, self._region_name)
            invocation: CommandInvocation = await instance_command_runner\
                .run_commands(config["server"]["games"][self._current_game]["commands"]["query-player-count"])
            player_count: int = int(invocation.output) if invocation.status == CommandStatus.SUCCESS and invocation.output.isdigit() else 0

            if player_count != 0:
                self._instance_query_no_players_count = -1
                return

            self._instance_query_no_players_count += 1

            message_text: str = f"The server is running and no one has been playing {self._current_game} for "\
                f"{self._instance_query_no_players_count * config['server']['auto-shutdown-query-delay']} minutes. "
            if self._instance_query_no_players_count < round(config["server"]["auto-shutdown-delay"] / config["server"]["auto-shutdown-query-delay"]):
                if self._instance_query_no_players_count > 0:
                    await message_util.send_simple_here_mention_to_channel(self._bot, config["server"]["command-channel"])
                    message_text += f"Please run `{self._bot.command_prefix}server stop` to stop the server if you're finished playing!"
                    await message_util.send_simple_embed_to_channel(self._bot, config["server"]["command-channel"], message_text)
            else:
                await message_util.send_simple_here_mention_to_channel(self._bot, config["server"]["command-channel"])
                message_text += "The server will now be automatically shut down."
                await message_util.send_simple_embed_to_channel(self._bot, config["server"]["command-channel"], message_text)

                # Stop the current game
                await instance_command_runner.run_commands(config["server"]["games"][self._current_game]["commands"]["stop"])

                # Stop the instance
                await instance_manager.stop_instance()

                # Clear the current game and the bot activity
                await self._set_current_game(None)

                # Stop the instance query loop
                self.query_instance_usage.stop()

    @query_instance_usage.error # type: ignore[arg-type]
    async def query_instance_usage_error(self, exception: Exception) -> None:
        """Error handler for the instance query loop, which prints an error message based on the error raised.

        Args:
            exception (commands.CommandError): The exception which was thrown by the command.
        """
        await error_util.log_error(_log, self._bot, exception)

    # *** _log_command_error ****************************************************

    async def _log_command_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        if isinstance(exception, ServerMaintenanceInProgress):
            await message_util.send_simple_embed(context, f"The command `{self._bot.command_prefix}{context.command}` is currently disabled, as the "
                                                 "server as it is currently undergoing maintenance. Please try again later.")
        else:
            await error_util.log_command_error(_log, self._bot, context, exception)

    # *** _check_valid_game *****************************************************

    @staticmethod
    def _check_valid_game(game: str) -> None:
        if game not in config["server"]["games"]:
            raise InvalidGameError(game)

    # *** _check_no_maintenance *************************************************

    def _check_no_maintenance(self) -> None:
        if self._maintenance:
            raise ServerMaintenanceInProgress()

    # *** _check_game_not_running ***********************************************

    def _check_game_not_running(self, game: str) -> None:
        if game == self._current_game:
            raise GameAlreadyRunningError(game)

    # *** _warn_instance_running_without_game ***********************************

    async def _warn_instance_running_without_game(self) -> None:
        """Print a warning that the instance is running, but the current_game is None."""
        await error_util.log_warning(_log, self._bot, "Instance is running, but no game server is running on it")

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

        self._current_game = game

        activity: Optional[discord.activity.Game] = discord.Game(game) if game else None
        await self._bot.change_presence(activity = activity)

    # *** _get_state_color ******************************************************

    @staticmethod
    def _get_state_color(instance_state: InstanceState) -> str:
        """Return a string containing the emote colour for the current AWS instance state.

        Raises:
            ValueError: Raised if the instance description isn't set.

        Returns:
            str: The colour for the current state.
        """
        if instance_state == InstanceState.RUNNING:
            return "green"
        if instance_state == InstanceState.STOPPED:
            return "red"
        if instance_state == InstanceState.PENDING:
            return "yellow"
        if instance_state == InstanceState.STOPPING:
            return "orange"

        return "black"
