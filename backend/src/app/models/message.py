from sqlalchemy import (
    Index,
    Column,
    String,
    DateTime,
    ForeignKeyConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSON

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, nullable=False)
    author = Column(JSON, nullable=True)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, content={self.content}, created_at={self.created_at})>"

    __table_args__ = (
        Index("ix_messages_id", id),
        Index("ix_messages_conversation_id", conversation_id),
        ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_message_conversation",
            ondelete="CASCADE",
        ),
    )


Message.metadata = Column(JSON, nullable=True)
