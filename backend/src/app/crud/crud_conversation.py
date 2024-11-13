from typing import List

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.crud_base import CRUDBaseAsync
from ..utils.id_generator import generate_id
from ..models.conversation import Conversation
from ..schemas.conversation import ConversationCreate, ConversationUpdate


class CRUDConversation(CRUDBaseAsync[Conversation, ConversationCreate, ConversationUpdate]):
    async def create_with_id(
        self,
        db: AsyncSession,
        *,
        obj_in: ConversationCreate,
    ) -> Conversation:
        obj_in_data = obj_in.model_dump(exclude_none=True, exclude_unset=True)
        db_obj = self.model(**obj_in_data, id=generate_id(prefix="conv_"))

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_multi_by_author(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[Conversation]:
        stmt = select(Conversation).order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_multi_by_workspace(
        self, db: AsyncSession, *, workspace_id: str, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        stmt = select(Conversation).filter(Conversation.workspace_id == workspace_id).offset(skip).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_conversation_timestamp(self, db: AsyncSession, conversation_id: str) -> None:
        stmt = update(Conversation).where(Conversation.id == conversation_id).values(updated_at=func.now())
        await db.execute(stmt)
        await db.commit()

    async def get_by_title(self, db: AsyncSession, title: str) -> Conversation | None:
        stmt = select(self.model).where(self.model.title == title)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


conversation = CRUDConversation(Conversation)
