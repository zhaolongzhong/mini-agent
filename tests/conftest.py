# tests/conftest.py
import asyncio
import logging
from typing import Iterator

import pytest

from cue.utils.logs import setup_logging
from cue.llm.llm_model import ChatModel

# Global configuration dictionary
test_config = {"default_model": ChatModel.GPT_4O_MINI}


@pytest.fixture(scope="session")
def default_chat_model() -> str:
    """Fixture to provide the default ChatModel for tests."""
    return test_config["default_model"].id


@pytest.fixture(scope="session", autouse=True)
def configure_logging_fixture():
    setup_logging()
    yield
    # Teardown: Close all handlers to release file resources
    logger = logging.getLogger()
    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)


# Function to change the default model (can be called from tests if needed)
def set_default_model(model: str) -> None:
    """Set the default model for tests."""
    test_config["default_model"] = model


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
