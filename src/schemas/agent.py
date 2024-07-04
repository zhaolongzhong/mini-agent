from memory.memory import StorageType
from pydantic import BaseModel


class AgentConfig(BaseModel):
    id: str
    name: str | None = None
    model: str
    tools: list[str] = []
    enable_planning: bool = False
    storage_type: StorageType = StorageType.IN_MEMORY
