from sqlalchemy import (
    Index,
    Column,
    String,
    DateTime,
    ForeignKeyConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSON

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    assistant_id = Column(String, nullable=True)

    assistant = relationship("Assistant")

    __table_args__ = (
        Index("ix_conversations_id", id),
        ForeignKeyConstraint(
            ["assistant_id"],
            ["assistants.id"],
            name="fk_conversation_assistant",
            ondelete="SET DEFAULT",
        ),
    )


Conversation.metadata = Column(JSON, nullable=True)
