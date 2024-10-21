# src/cue/schemas/agent_config.py
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..llm.llm_model import ChatModel
from ..tools._tool import Tool
from .feature_flag import FeatureFlag
from .storage_type import StorageType


class AgentConfig(BaseModel):
    id: Optional[str] = "default_id"
    name: Optional[str] = "default_name"
    description: Optional[str] = None
    model: Optional[ChatModel] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = 0.8
    max_tokens: Optional[int] = 1000
    stop_sequences: Optional[list[str]] = None
    system_message: Optional[str] = None
    tools: Optional[list[Tool]] = None
    conversation_id: Optional[str] = None
    max_actions: Optional[int] = 10
    storage_type: Optional[Any] = StorageType.IN_MEMORY
    feature_flag: FeatureFlag = Field(default_factory=FeatureFlag)
    is_test: bool = False
