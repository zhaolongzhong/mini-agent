import uuid
import logging
from typing import List, Tuple, Optional

import numpy as np
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assistant_memory import AssistantMemory, AssistantMemoryEmbedding


class MemoryManager:
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.logger = logging.getLogger(__name__)

    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for given text using OpenAI API."""
        try:
            text = text.replace("\n", " ")
            response = await self.client.embeddings.create(input=[text], model=self.model)
            embedding = response["data"][0]["embedding"]
            return embedding
        except Exception as e:
            self.logger.error(f"Error creating embedding: {e}")
            raise

    async def store_memory(
        self,
        db: AsyncSession,
        content: str,
        assistant_id: str,
        metadata: Optional[dict] = None,
    ) -> AssistantMemory:
        """Store memory content and its embedding."""
        try:
            # Create memory entry
            if not metadata:
                metadata = {}
            metadata["model"] = self.model
            memory = AssistantMemory(
                id=str(uuid.uuid4()),
                assistant_id=assistant_id,
                content=content,
                metadata=metadata,
            )
            db.add(memory)
            await db.flush()  # Ensure memory.id is available

            # Create and store embedding
            embedding = await self.create_embedding(content)
            memory_embedding = AssistantMemoryEmbedding(
                id=str(uuid.uuid4()), assistant_memory_id=memory.id, embedding=embedding
            )
            db.add(memory_embedding)

            await db.commit()
            await db.refresh(memory)
            return memory
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error storing memory: {e}")
            raise

    async def search_similar_memories(
        self, db: AsyncSession, query: str, assistant_id: str, limit: int = 5
    ) -> List[Tuple[AssistantMemory, float]]:
        """Search for similar memories using cosine similarity."""
        try:
            # Get query embedding
            query_embedding = await self.create_embedding(query)
            query_embedding_array = np.array(query_embedding)

            # Fetch relevant embeddings with eager loading
            stmt = (
                select(AssistantMemoryEmbedding)
                .options(selectinload(AssistantMemoryEmbedding.memory))
                .where(AssistantMemoryEmbedding.memory.has(assistant_id=assistant_id))
            )

            result = await db.execute(stmt)
            embeddings = result.scalars().all()

            # Convert embeddings to numpy array for vectorized operations
            embedding_matrix = np.array([emb.embedding for emb in embeddings])

            # Normalize embeddings to unit vectors
            norm_query = query_embedding_array / np.linalg.norm(query_embedding_array)
            norm_embeddings = embedding_matrix / np.linalg.norm(embedding_matrix, axis=1, keepdims=True)

            # Compute cosine similarities
            similarities = np.dot(norm_embeddings, norm_query)

            # Pair memories with similarities
            paired = list(zip([emb.memory for emb in embeddings], similarities, strict=False))

            # Sort by similarity and return top results
            paired.sort(key=lambda x: x[1], reverse=True)
            return paired[:limit]
        except Exception as e:
            self.logger.error(f"Error searching memories: {e}")
            raise
