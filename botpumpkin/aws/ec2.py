"""A collection of classes to assist with using an AWS EC2 client from the boto3 library."""
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Awaitable, Literal, Optional, Union

# Third party imports
import boto3
import discord.ext.commands as commands
from mypy_boto3_ec2.client import EC2Client
from mypy_boto3_ec2.type_defs import DescribeInstancesResultTypeDef

_log: logging.Logger = logging.getLogger(__name__)


# *** NoInstanceDescriptionError ********************************************

class NoInstanceDescriptionError(commands.CommandError):
    """Exception which is raised when no instance is returned from a request for instance descriptions from AWS."""

    def __init__(self) -> None:
        """Initialize a NoInstanceDescriptionError exception."""
        super().__init__("Expected an instance description, but none were found")


# *** InstanceState *********************************************************

class InstanceState(Enum):
    """The various valid states of an AWS EC2 instance."""

    PENDING = "pending"
    RUNNING = "running"
    SHUTTING_DOWN = "shutting-down"
    TERMINATED = "terminated"
    STOPPING = "stopping"
    STOPPED = "stopped"


# *** InstanceDescription ***************************************************

class InstanceDescription:
    """The configuration information for an AWS EC2 instance. information of an AWS System Manager command invocation.

    Attributes:
        state (InstanceState): The state of the EC2 instance.
        image_id (str): The status id of the EC2 instance.
        launch_time (datetime): The last time the instance was launched.
        public_ip_address (Optional[str]): The output of the command invocation.
        public_dns_name (Optional[str]): The output of the command invocation.
    """

    def __init__(self, instance_description: DescribeInstancesResultTypeDef) -> None:
        """Initialize an InstanceDescription using the response from a call to boto3.client.describe_instances.

        Args:
            instance_description (DescribeInstancesResultTypeDef): The dictionary returned by boto3.client.describe_instances.

        Raises:
            NoInstanceDescriptionError: Raised when no instance descriptions are returned.
        """
        if len(instance_description["Reservations"]) == 0 or len(instance_description["Reservations"][0]["Instances"]) == 0:
            raise NoInstanceDescriptionError()

        instance = instance_description["Reservations"][0]["Instances"][0]
        self.state: InstanceState = InstanceState(instance["State"]["Name"])
        self.image_id: str = instance["ImageId"]
        self.launch_time: datetime = instance["LaunchTime"]
        self.public_ip_address: Optional[str] = instance["PublicIpAddress"] if "PublicIpAddress" in instance else ""
        self.public_dns_name: Optional[str] = instance["PublicDnsName"] if "PublicDnsName" in instance else ""

    def __str__(self) -> str:
        """Return a string of basic instance description information.

        Returns:
            str: Basic instance description information.
        """
        return f"Instance description: {{ image_id: {self.image_id}, state: {self.state} }}"


# *** InstanceManager *******************************************************

class InstanceManager:
    """Performs management of an AWS EC2 instance."""

    def __init__(self, instance_id: str, aws_access_key_id: str, aws_secret_access_key: str, region_name: str) -> None:
        """Initialize an InstanceManager, creating an AWS client connection using the provided parameters.

        Args:
            instance_id (str): The id of the instance.
            aws_access_key_id (str): The AWS access key id for the account which has access to the instance.
            aws_secret_access_key (str): The AWS secret access key for the account which has access to the instance.
            region_name (str): The name of the region where the instance is running.
        """
        self._client: EC2Client = boto3.client("ec2", aws_access_key_id = aws_access_key_id, aws_secret_access_key = aws_secret_access_key,
                                               region_name = region_name)
        self._instance_id: str = instance_id

    # *** get_instance_description **********************************************

    def get_instance_description(self) -> InstanceDescription:
        """Get the instance description for an AWS EC2 instance with the configured id.

        Returns:
            InstanceDescription: The description of the instance.
        """
        response: DescribeInstancesResultTypeDef = self._client.describe_instances(InstanceIds = [self._instance_id])
        description: InstanceDescription = InstanceDescription(response)
        _log.info(description)
        return description

    # *** start_instance ********************************************************

    async def start_instance(self) -> InstanceDescription:
        """Start the AWS EC2 instance with the configured id and query it until it is running.

        Returns:
            InstanceDescription: The description of the started instance.
        """
        self._client.start_instances(InstanceIds = [self._instance_id])
        await self._get_instance_state_change_waiter("instance_running")
        return self.get_instance_description()

    # *** stop_instance *********************************************************

    async def stop_instance(self) -> InstanceDescription:
        """Stop the AWS EC2 instance with the configured id and query it until it is stopped.

        Returns:
            InstanceDescription: The description of the stopped instance.
        """
        self._client.stop_instances(InstanceIds = [self._instance_id])
        await self._get_instance_state_change_waiter("instance_stopped")
        return self.get_instance_description()

    # *** _get_instance_state_change_waiter *************************************

    def _get_instance_state_change_waiter(self, waiter_name: Union[Literal["instance_running", "instance_stopped"]]) -> Awaitable:
        """Return an awaitable which waits until the instance has the desired state.

        Args:
            waiter_name (Union[Literal[): The name of the AWS EC2 waiter to use.

        Returns:
            Awaitable: An awaitable function which waits until the instance state has changed.
        """
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: self._client.get_waiter(waiter_name).wait(InstanceIds = [self._instance_id]))
