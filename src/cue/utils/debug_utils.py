import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def debug_print_messages(messages: List[Dict[str, Any]], indent: int = 2, tag: Optional[str] = None) -> None:
    """
    Pretty prints a list of message dictionaries.

    Args:
    messages (List[Dict[str, Any]]): The list of message dictionaries to print.
    indent (int): The number of spaces to use for indentation. Default is 2.
    """
    try:
        size = len(messages)
        for i, message in enumerate(messages, 1):
            if isinstance(message, BaseModel):
                message = message.model_dump()
            if isinstance(message, dict) or isinstance(message, list):
                logger.debug(f"{tag} Message {i}/{size}: {json.dumps(message, indent=indent + 2)}")
            else:
                logger.debug(f"{tag} Message {i}/{size}: {message}")

    except Exception as e:
        logger.error(f"debug_print error: {e}")
