import uuid
from typing import List, Tuple, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .crud_base import CRUDBaseAsync
from ..models.assistant_memory import AssistantMemoryEmbedding
from ..schemas.assistant_memory_embedding import (
    AssistantMemoryEmbeddingCreate,
    AssistantMemoryEmbeddingUpdate,
)


class CRUDAssistantMemoryEmbedding(
    CRUDBaseAsync[
        AssistantMemoryEmbedding,
        AssistantMemoryEmbeddingCreate,
        AssistantMemoryEmbeddingUpdate,
    ]
):
    async def create_with_memory(
        self,
        db: AsyncSession,
        *,
        obj_in: AssistantMemoryEmbeddingCreate,
    ) -> AssistantMemoryEmbedding:
        obj_in_data = obj_in.model_dump(exclude_none=True, exclude_unset=True)
        db_obj = self.model(
            **obj_in_data,
            id=str(uuid.uuid4()),
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_memory_id(
        self, db: AsyncSession, *, assistant_memory_id: str
    ) -> Optional[AssistantMemoryEmbedding]:
        query = select(self.model).filter(AssistantMemoryEmbedding.assistant_memory_id == assistant_memory_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_embeddings_by_assistant(self, db: AsyncSession, assistant_id: str) -> List[Tuple[str, List[float]]]:
        query = select(
            AssistantMemoryEmbedding.assistant_memory_id,
            AssistantMemoryEmbedding.embedding,
        ).filter(AssistantMemoryEmbedding.assistant_id == assistant_id)
        result = await db.execute(query)
        return result.all()


assistant_memory_embedding = CRUDAssistantMemoryEmbedding(AssistantMemoryEmbedding)
