"""A collection of classes to assist with using an AWS System Manager client from the boto3 library."""
import asyncio
import logging
from enum import Enum
from typing import List

# Third party imports
import boto3
import botocore
import discord.ext.commands as commands
from mypy_boto3_ssm.client import SSMClient
from mypy_boto3_ssm.type_defs import GetCommandInvocationResultTypeDef, SendCommandResultTypeDef

# First party imports
from botpumpkin.aws.error import client_error_is_instance

_log: logging.Logger = logging.getLogger(__name__)


# *** CommandExceededAttempts ***********************************************

class CommandExceededAttempts(commands.CommandError):
    """Exception which is raised when a command exceeds the number of attempts to execute successfully."""

    def __init__(self) -> None:
        """Initialize a CommandExceededAttempts exception."""
        super().__init__("Command failed to execute successfully on the instance")


# *** CommandExceededWaitTime ***********************************************

class CommandExceededWaitTime(commands.CommandError):
    """Exception which is raised when a command doesn't finish before the allotted number of status queries."""

    def __init__(self) -> None:
        """Initialize a CommandExceededWaitTime exception."""
        super().__init__("Command failed to finish executing within the allotted time")


# *** CommandStatus *********************************************************

class CommandStatus(Enum):
    """The various valid statuses of an AWS System Manager command."""

    PENDING = "Pending"
    IN_PROGRESS = "InProgress"
    DELAYED = "Delayed"
    SUCCESS = "Success"
    CANCELLED = "Cancelled"
    FAILED = "Failed"
    TIMED_OUT = "TimedOut"
    CANCELLING = "Cancelling"


# *** CommandInvocation *****************************************************

class CommandInvocation:
    """The status information of an AWS System Manager command invocation.

    Attributes:
        commands (List[str]): The list of commands that were run in this invocation.
        status (CommandStatus): The status of the command invocation.
        output (str): The output of the command invocation.
        error_output (str): The error output of the command invocation.
    """

    def __init__(self, command_invocation: GetCommandInvocationResultTypeDef, instance_commands: List[str]) -> None:
        """Initialize a CommandInvocation using the response from a call to boto3.client.get_command_invocation.

        Args:
            command_invocation (GetCommandInvocationResultTypeDef): The dictionary returned by boto3.client.get_command_invocation.
            instance_commands (List[str]): The list of commands which were run on the instance.
        """
        self.instance_commands: List[str] = instance_commands
        self.status: CommandStatus = CommandStatus(command_invocation["Status"])
        self.output: str = command_invocation["StandardOutputContent"].strip()
        self.error_output: str = command_invocation["StandardErrorContent"].strip()

    def __str__(self) -> str:
        """Return a string of basic command invocation information.

        Returns:
            str: Basic command invocation information.
        """
        return f"Command invocation: {{ status: {self.status}, commands: {self.instance_commands}, output: {self.output} }}"


# *** InstanceCommandRunner *************************************************

class InstanceCommandRunner:
    """Runs commands on an AWS instance using the AWS System Manager."""

    _COMMAND_SEND_ATTEMPT_MAX = 20
    _COMMAND_SEND_SEC_DELAY = 5
    _COMMAND_QUERY_ATTEMPT_MAX = 40
    _COMMAND_QUERY_SEC_DELAY = 1
    _COMMAND_RETRY_MAX = 40
    _COMMAND_RETRY_SEC_DELAY = 15

    def __init__(self, instance_id: str, aws_access_key_id: str, aws_secret_access_key: str, region_name: str) -> None:
        """Initialize an InstanceCommandRunning, creating an AWS client connection using the provided parameters.

        Args:
            instance_id (str): The id of the instance.
            aws_access_key_id (str): The AWS access key id for the account which has access to the instance.
            aws_secret_access_key (str): The AWS secret access key for the account which has access to the instance.
            region_name (str): The name of the region where the instance is running.
        """
        self._client: SSMClient = boto3.client("ssm", aws_access_key_id = aws_access_key_id, aws_secret_access_key = aws_secret_access_key,
                                               region_name = region_name)
        self._instance_id: str = instance_id

    # *** run_commands **********************************************************

    async def run_commands(self, instance_commands: list[str]) -> CommandInvocation:
        """Run a set of commands on an AWS instance using an AWS System Manager.

        Args:
            instance_commands (list[str]): The list of commands to run on the AWS instance.

        Raises:
            exception: Raised when an unexpected exception is thrown from a call to boto3.client.send_command or boto3.client.get_command_invocation
            CommandExceededWaitTime: Raised when a command doesn't return a "finished" status after the configured number of queries

        Returns:
            CommandInvocation: The status information of the command invocation.
        """
        # Repeatedly attempt to send the command to the instance with the given id, as the instance may not have finished starting
        success: bool = False
        attempts: int = 0
        while not success:
            attempts += 1
            try:
                response: SendCommandResultTypeDef = self._client.send_command(DocumentName = "AWS-RunShellScript",
                                                                               Parameters = {"commands": instance_commands},
                                                                               InstanceIds = [self._instance_id])
                success = True
            except botocore.exceptions.ClientError as exception:
                # If an InvalidInstanceId error occurs, the instance probably hasn't finished starting yet, so delay and try again
                if not client_error_is_instance(exception, "InvalidInstanceId") or attempts >= InstanceCommandRunner._COMMAND_SEND_ATTEMPT_MAX:
                    raise exception

                await asyncio.sleep(InstanceCommandRunner._COMMAND_SEND_SEC_DELAY)

        command_id: str = response["Command"]["CommandId"]

        # Repeatedly attempt to query the status of the command invocation, as the invocation may not have been created yet
        attempts = 0
        while True:
            attempts += 1
            try:
                command_invocation: CommandInvocation = await self._get_command_invocation(command_id, instance_commands)
                if command_invocation.status not in [CommandStatus.PENDING, CommandStatus.IN_PROGRESS, CommandStatus.DELAYED]:
                    return command_invocation

                if attempts >= InstanceCommandRunner._COMMAND_QUERY_ATTEMPT_MAX:
                    raise CommandExceededWaitTime()
            except botocore.exceptions.ClientError as exception:
                # If an InvocationDoesNotExist error occurs, the command invocation probably hasn't been created yet, so delay and try again
                if not client_error_is_instance(exception, "InvocationDoesNotExist") or attempts >= InstanceCommandRunner._COMMAND_QUERY_ATTEMPT_MAX:
                    raise exception

            await asyncio.sleep(InstanceCommandRunner._COMMAND_QUERY_SEC_DELAY)

    # *** run_commands_until_success ********************************************

    async def run_commands_until_success(self, instance_commands: list[str]) -> CommandInvocation:
        """Run a set of commands on an AWS instance using an AWS System Manager until the command runs successfully.

        Args:
            instance_commands (list[str]): The list of commands to run on an AWS instance.

        Raises:
            exception: Raised when an unexpected exception is thrown from a call to boto3.client.run_commands
            CommandExceededAttempts: Raised when the commands don't run successfully after _COMMAND_RETRY_MAX attempts.
        """
        attempts: int = 0
        while True:
            attempts += 1
            command_invocation: CommandInvocation = await self.run_commands(instance_commands)
            if command_invocation.status != CommandStatus.SUCCESS:
                if attempts >= InstanceCommandRunner._COMMAND_RETRY_MAX:
                    raise CommandExceededAttempts()
                await asyncio.sleep(InstanceCommandRunner._COMMAND_RETRY_SEC_DELAY)
            else:
                return command_invocation

    # *** _get_command_invocation ***********************************************

    async def _get_command_invocation(self, command_id: str, instance_commands: List[str]) -> CommandInvocation:
        """Get the status information for the AWS System Manager command invocation with the given id.

        Args:
            command_id (str): The id of the AWS System Manager command invocation.

        Returns:
            CommandInvocation: The status information of the command invocation.
        """
        response: GetCommandInvocationResultTypeDef = self._client.get_command_invocation(CommandId = command_id, InstanceId = self._instance_id)
        invocation: CommandInvocation = CommandInvocation(response, instance_commands)
        _log.info(invocation)
        return invocation
