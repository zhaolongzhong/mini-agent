# tests/conftest.py
import logging

import pytest
from cue.utils.logs import setup_logging


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
