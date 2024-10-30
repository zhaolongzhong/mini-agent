import os
import json
import logging
from typing import Any, Dict, List, Union, Optional
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DebugUtils:
    @staticmethod
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
            # when it's image, Object of type SerializationIterator is not JSON serializable
            if "SerializationIterator" not in str(e):
                logger.error(f"debug_print error: {e}")
            else:
                logger.debug("debug_print skip print last message, it might be image")
        logger.debug("debug_print skip print last message, it might be image")

    @staticmethod
    def _serialize_message(msg: Union[Dict, BaseModel]) -> Dict[str, Any]:
        """
        Convert message to a serializable dictionary
        """
        if isinstance(msg, BaseModel):
            return msg.model_dump()
        return msg

    @staticmethod
    def take_snapshot(messages: List[Union[Dict, BaseModel]], pretty: bool = True, suffix: Optional[str] = None):
        """
        Record current message list to a file in JSONL format

        Args:
            messages: List of messages. Each message can be:
                - Dictionary
                - Pydantic BaseModel
            pretty: If True, format the JSON with indentation for better readability
            suffix: If provided, append it at the end otherwise use timestamp

        Returns:
            Path: Path to the created snapshot file
        """
        if not messages:
            return

        if suffix:
            filename_suffix = suffix
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_suffix = timestamp

        base_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

        if pretty:
            file_name = f"snapshot_{filename_suffix}_readable.json"
            snapshot_path = base_dir / "logs/snapshot" / file_name
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            serialized_messages = [DebugUtils._serialize_message(msg) for msg in messages]

            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(serialized_messages, f, ensure_ascii=False, indent=2)

        file_name = f"snapshot_{filename_suffix}.jsonl"
        snapshot_path = base_dir / "logs/snapshot" / file_name
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        with open(snapshot_path, "w", encoding="utf-8") as f:
            for msg in messages:
                serialized_msg = DebugUtils._serialize_message(msg)
                json.dump(serialized_msg, f, ensure_ascii=False)
                f.write("\n")

        return snapshot_path

    def read_snapshot(self, file_path: Path):
        """
        Read and display contents of a snapshot file
        """
        if file_path.suffix == ".jsonl":
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    print(json.loads(line))
        else:
            with open(file_path, encoding="utf-8") as f:
                print(json.load(f))
