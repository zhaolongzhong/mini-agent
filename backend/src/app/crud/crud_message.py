import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .crud_base import CRUDBaseAsync
from ..models.message import Message
from ..schemas.message import MessageCreate, MessageUpdate


class CRUDMessage(CRUDBaseAsync[Message, MessageCreate, MessageUpdate]):
    async def create_with_id(
        self,
        db: AsyncSession,
        *,
        obj_in: MessageCreate,
    ) -> Message:
        obj_in_data = obj_in.model_dump()
        db_obj = Message(
            **obj_in_data,
            id=str(uuid.uuid4()),
        )

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_multi_by_conversation_id_desc(
        self, db: AsyncSession, *, conversation_id: str, skip: int = 0, limit: int = 25
    ) -> list[Message]:
        stmt = (
            select(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_multi_since(
        self,
        db: AsyncSession,
        *,
        conversation_id: str,
        since: datetime,  # exclusive
        skip: int = 0,
        limit: int = 100,
    ) -> list[Message]:
        stmt = (
            select(Message)
            .filter(Message.conversation_id == conversation_id)
            .filter(Message.created_at > since)
            .order_by(desc(Message.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


message = CRUDMessage(Message)
