from sqlalchemy import (
    Index,
    Column,
    String,
    DateTime,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSON

from app.database import Base


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_assistants_id", id),)


Assistant.metadata = Column(JSON, nullable=True)
