import logging
import os

from rich.console import Console
from rich.style import Style
from rich.theme import Theme
from utils.cli_utils import clear_line

_logger: logging.Logger = logging.getLogger("mini-agent")


class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Use the first character of the log level name
        record.levelname = record.levelname[0]
        return super().format(record)


class ConsoleHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        # key: d=debug, i=info, w=warning, e=error
        theme = Theme(
            {
                "d": Style(color="grey54"),
                "i": "cyan",
                "w": "magenta",
                "e": "bold red",
            }
        )
        style = str(record.levelname).lower().strip()
        # Set markup to True to strip out [] in tag in message
        console = Console(theme=theme, markup=False)
        console.print(msg, style=style)


def _basic_config() -> None:
    console_handler = ConsoleHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = CustomFormatter(
        fmt="[%(asctime)s - %(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)


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
