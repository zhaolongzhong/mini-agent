from typing import Dict, List, Optional

from pydantic import BaseModel


class AssistantMemoryEmbeddingBase(BaseModel):
    embedding: List[float]


class AssistantMemoryEmbeddingCreate(AssistantMemoryEmbeddingBase):
    assistant_memory_id: str
    assistant_id: str


class AssistantMemoryEmbeddingUpdate(BaseModel):
    embedding: Optional[Dict] = None


class AssistantMemoryEmbeddingInDBBase(AssistantMemoryEmbeddingBase):
    id: str
    assistant_memory_id: str
    assistant_id: str

    class ConfigDict:
        from_attributes = True


class AssistantMemoryEmbedding(AssistantMemoryEmbeddingInDBBase):
    pass
