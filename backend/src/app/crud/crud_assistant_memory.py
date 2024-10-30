from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_base import CRUDBaseAsync
from app.utils.id_generator import generate_id
from app.models.assistant_memory import AssistantMemory
from app.schemas.assistant_memory import AssistantMemoryCreate, AssistantMemoryUpdate


class CRUDAssistantMemory(CRUDBaseAsync[AssistantMemory, AssistantMemoryCreate, AssistantMemoryUpdate]):
    async def create_with_assistant(self, db: AsyncSession, *, obj_in: AssistantMemoryCreate) -> AssistantMemory:
        obj_in_data = obj_in.model_dump(exclude_none=True, exclude_unset=True)
        db_obj = self.model(
            **obj_in_data,
            id=generate_id(prefix="mem_"),
        )

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_multi_by_assistant(
        self, db: AsyncSession, *, assistant_id: str, skip: int = 0, limit: int = 32
    ) -> List[AssistantMemory]:
        query = (
            select(self.model)
            .filter(AssistantMemory.assistant_id == assistant_id)
            .order_by(desc(self.model.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_id_and_assistant(
        self, db: AsyncSession, *, id: str, assistant_id: str
    ) -> Optional[AssistantMemory]:
        query = select(self.model).filter(AssistantMemory.id == id, AssistantMemory.assistant_id == assistant_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_memories_by_ids(self, db: AsyncSession, memory_ids: List[str]) -> List[AssistantMemory]:
        query = select(self.model).filter(AssistantMemory.id.in_(memory_ids))
        result = await db.execute(query)
        return result.scalars().all()


assistant_memory = CRUDAssistantMemory(AssistantMemory)
