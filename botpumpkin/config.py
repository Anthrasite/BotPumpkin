"""Provides a single class which provides configuration access and manipulation, and initializes it."""
import json
import logging
import pathlib
import sys
from datetime import datetime
from logging import handlers
from typing import Any, Iterator

# Third party imports
from dotenv import load_dotenv


# *** InstanceState *********************************************************

class Configuration():
    """Simple configuration dictionary which reads configuration values from a config.json file and automatically saves changes back to the file."""

    def __init__(self) -> None:
        """Initialize the Configuration by reading from the config.json file and loading it into a dict."""
        self._config_file_path = pathlib.Path(__file__).parent.joinpath("config.json")
        with open(self._config_file_path, "r") as file:
            self._config: Any = json.load(file)

    def __getitem__(self, key: str) -> Any:
        """Retrieve an item from the configuration dictionary based on the provided key.

        Args:
            key (str): The key to retrieve from the configuration dictionary.

        Returns:
            Any: The value in the configuration dictionary.
        """
        return self._config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Change the value of an item in the configuration dictionary to the provided value based on the provided key.

        Args:
            key (str): The key to the value to change in the configuration dictionary.
            value (Any): The value to set in the configuration dictionary.
        """
        self._config[key] = value
        with open(self._config_file_path, "w") as file:
            json.dump(self._config, file)

    def __iter__(self) -> Iterator:
        """Return an interator for the configuration.

        Returns:
            Iterator: An iterator of the configuration dictionary

        Yields:
            Iterator: An iterator of the configuration dictionary
        """
        return iter(self._config)

    def is_cog_enabled(self, cog_name: str) -> bool:
        """Return whether the cog with the given name is enabled.

        Args:
            cog_name (str): The cog to check the status of.

        Returns:
            bool: Whether the cog is enabled.
        """
        return cog_name in self._config and self._config[cog_name]["enabled"]


# *** _setup_logging ********************************************************

def _setup_logging() -> None:
    """Set up console and file logging."""
    log_level: int = logging.INFO
    log_format: logging.Formatter = logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s")

    log_file_name: pathlib.Path = pathlib.Path(__file__).parent.parent.joinpath("logs").joinpath("{:%y%m%d%H%M%S}.BotPumpkin.log".format(datetime.now()))
    log_file_handler: handlers.RotatingFileHandler = handlers.RotatingFileHandler(filename = log_file_name, maxBytes = 10485760, backupCount = 10, encoding = "utf-8", mode = "w")
    log_file_handler.setFormatter(log_format)

    log_console_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    log_console_handler.setFormatter(log_format)

    logger: logging.Logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(log_file_handler)
    logger.addHandler(log_console_handler)


# Initialize logging and environment variables once on module load
_setup_logging()
load_dotenv()
config: Configuration = Configuration()
