from sqlalchemy import (
    Index,
    Column,
    String,
    DateTime,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSON

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_conversations_id", id),)


Conversation.metadata = Column(JSON, nullable=True)
