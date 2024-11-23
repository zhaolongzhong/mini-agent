from sqlalchemy import Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_base import CRUDBaseAsync
from app.models.assistant import Assistant
from app.schemas.assistant import AssistantCreate, AssistantUpdate
from app.utils.id_generator import generate_id


class CRUDAssistant(CRUDBaseAsync[Assistant, AssistantCreate, AssistantUpdate]):
    async def create_with_id(self, db: AsyncSession, *, obj_in: AssistantCreate) -> Assistant:
        obj_in_data = obj_in.model_dump(exclude_none=True, exclude_unset=True)
        db_obj = self.model(**obj_in_data, id=generate_id(prefix="asst_"))

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_first(self, db: AsyncSession) -> Assistant | None:
        """
        Get the first assistant from the database.
        Returns None if no assistant exists.
        """
        stmt = select(self.model).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, name: str) -> Assistant | None:
        """
        Get an assistant by name.
        Returns None if no assistant with the given name exists.
        """
        stmt = select(self.model).where(self.model.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_primary(self, db: AsyncSession) -> Assistant | None:
        """
        Get primary assistant.
        """
        stmt = select(self.model).where(self.model.metadata["is_primary"].astext.cast(Boolean) is True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


assistant = CRUDAssistant(Assistant)
