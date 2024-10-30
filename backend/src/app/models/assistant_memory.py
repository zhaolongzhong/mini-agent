import uuid

from sqlalchemy import Text, Index, Column, String, DateTime, ForeignKeyConstraint, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON, JSONB

from app.database import Base


class AssistantMemory(Base):
    __tablename__ = "assistant_memories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assistant_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    embedding = relationship(
        "AssistantMemoryEmbedding", back_populates="memory", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_assistant_memories_id", "id"),
        Index("ix_assistant_memories_assistant_id", "assistant_id"),
        ForeignKeyConstraint(
            ["assistant_id"],
            ["assistants.id"],
            name="fk_assistant_memory_assistant",
            ondelete="CASCADE",
        ),
    )

    def __repr__(self) -> str:
        return f"<AssistantMemory(id={self.id}, assistant_id={self.assistant_id}), content={self.content})>"


AssistantMemory.metadata = Column(JSON, nullable=True)


class AssistantMemoryEmbedding(Base):
    __tablename__ = "assistant_memory_embeddings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assistant_memory_id = Column(String, nullable=False)
    assistant_id = Column(String, nullable=False)
    embedding = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    memory = relationship("AssistantMemory", back_populates="embedding")

    __table_args__ = (
        Index("ix_assistant_memory_embeddings_memory_id", "assistant_memory_id"),
        ForeignKeyConstraint(
            ["assistant_memory_id"],
            ["assistant_memories.id"],
            name="fk_assistant_memory_assistant_memory_embedding",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["assistant_id"],
            ["assistants.id"],
            name="fk_assistant_memory_embedding_assistant",
            ondelete="CASCADE",
        ),
    )

    def __repr__(self) -> str:
        return f"<AssistantMemoryEmbedding(id={self.id}, memory_id={self.assistant_memory_id}, assistant_id={self.assistant_id})>"
