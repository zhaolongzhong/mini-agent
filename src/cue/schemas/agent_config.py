from typing import Any, Optional

from pydantic import BaseModel

from ..llm.llm_model import ChatModel
from .feature_flag import FeatureFlag
from .storage_type import StorageType


class AgentConfig(BaseModel):
    id: str = "default"
    name: str
    description: Optional[str] = None
    model: ChatModel
    temperature: float = 0.6
    max_tokens: int = 1000
    stop_sequences: Optional[list[str]] = None
    tools: Optional[list[Any]] = None
    conversation_id: Optional[str] = None
    max_actions: Optional[int] = 10
    system_message: Optional[str] = None
    storage_type: Optional[Any] = StorageType.FILE
    feature_flag: FeatureFlag = FeatureFlag()
    is_test: bool = False
