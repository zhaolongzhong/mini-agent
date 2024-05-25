import os
import logging

from utils.cli_utils import clear_line

_logger: logging.Logger = logging.getLogger("mini-agent")


def _basic_config() -> None:
    logging.basicConfig(
        format="[%(asctime)s - %(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logging() -> None:
    env = os.environ.get("LOG_LEVEL", "info")
    if env == "debug":
        _basic_config()
        _logger.setLevel(logging.DEBUG)
    elif env == "info":
        _basic_config()
        _logger.setLevel(logging.INFO)


class Logger:
    def __init__(self, name: str) -> None:
        self.logger = _logger
        self.name = name

    def debug(self, msg, *args, **kwargs):
        clear_line()
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        clear_line()
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        clear_line()
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        clear_line()
        self.logger.error(msg, *args, **kwargs)


logger = Logger("mini-agent")
