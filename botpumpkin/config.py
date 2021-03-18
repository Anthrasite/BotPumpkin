import logging
from logging import handlers
import pathlib
from datetime import datetime
import sys
import json
from collections.abc import MutableMapping

from dotenv import load_dotenv

def _setup_logging() -> None:
    """Set up logging"""
    log_level = logging.INFO
    log_format = logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s")

    log_file_name = pathlib.Path(__file__).parent.parent.joinpath("logs").joinpath("{:%y%m%d%H%M%S}.BotPumpkin.log".format(datetime.now()))
    log_file_handler = handlers.RotatingFileHandler(filename = log_file_name, maxBytes = 10485760, backupCount = 10, encoding = "utf-8", mode = "w")
    log_file_handler.setFormatter(log_format)

    log_console_handler = logging.StreamHandler(sys.stdout)
    log_console_handler.setFormatter(log_format)

    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(log_file_handler)
    logger.addHandler(log_console_handler)

def _load_env() -> None:
    """Load private keys into the environment variables"""
    load_dotenv()

class Configuration(MutableMapping):
    """Allows access to and modification of configuration information"""
    def __init__(self) -> None:
        self._config_file_path = pathlib.Path(__file__).parent.parent.joinpath("config.json")
        with open(self._config_file_path, "r") as file:
            self._config = json.load(file)

    def __getitem__(self, key):
        return self._config[key]

    def __setitem__(self, key, value):
        self._config[key] = value
        with open(self._config_file_path, "w") as file:
            json.dump(self._config, file)

    def __delitem__(self, key):
        del self._config[key]

    def __iter__(self):
        return iter(self._config)
    
    def __len__(self):
        return len(self._config)

# Initialize logging and environment variables once on module load
_setup_logging()
_load_env()
config = Configuration()