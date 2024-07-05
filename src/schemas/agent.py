from memory.memory import StorageType
from pydantic import BaseModel
from tools.tool_manager import Tool


class AgentConfig(BaseModel):
    id: str
    name: str | None = None
    model: str
    tools: list[Tool] = []
    enable_planning: bool = False
    storage_type: StorageType = StorageType.IN_MEMORY
