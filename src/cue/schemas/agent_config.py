# src/cue/schemas/agent_config.py
from typing import Any, Optional

from pydantic import Field, BaseModel

from .feature_flag import FeatureFlag


class AgentConfig(BaseModel):
    id: Optional[str] = "default_id"
    name: Optional[str] = "default_name"
    is_primary: Optional[bool] = False
    # Detailed description of agent's role, capabilities, and collaboration patterns
    description: Optional[str] = None
    # System message defining agent's behavior, collaboration guidelines, and boundaries
    instruction: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = 0.8
    max_tokens: Optional[int] = 1000
    stop_sequences: Optional[list[str]] = None
    tools: Optional[list[Any]] = []  # callable or tool enum
    conversation_id: Optional[str] = None
    max_actions: Optional[int] = 10
    enable_external_memory: bool = False
    feature_flag: FeatureFlag = Field(default_factory=FeatureFlag)
    is_test: bool = False
