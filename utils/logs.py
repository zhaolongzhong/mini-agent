import os
import logging

logger: logging.Logger = logging.getLogger("mini-agent")


def _basic_config() -> None:
    logging.basicConfig(
        format="[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logging() -> None:
    env = os.environ.get("LOG_LEVEL", "info")
    if env == "debug":
        _basic_config()
        logger.setLevel(logging.DEBUG)
    elif env == "info":
        _basic_config()
        logger.setLevel(logging.INFO)
