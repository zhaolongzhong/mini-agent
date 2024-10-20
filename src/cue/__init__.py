# src/cue/__init__.py
from pathlib import Path

from dotenv import load_dotenv

from ._agent import Agent
from ._agent_manager import AgentManager
from ._client import AsyncCueClient
from ._version import __title__, __version__
from .llm import ChatModel
from .schemas import AgentConfig, CompletionResponse, FeatureFlag, StorageType
from .tool_manager import Tool
from .utils.logs import setup_logging as _setup_logging

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

__all__ = [
    "__version__",
    "__title__",
    "Agent",
    "AgentConfig",
    "AgentManager",
    "AsyncCueClient",
    "ChatModel",
    "CompletionResponse",
    "FeatureFlag",
    "StorageType",
    "Tool",
]

_setup_logging()
