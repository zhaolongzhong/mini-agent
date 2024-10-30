import logging

import numpy as np
import openai
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.schemas.assistant_memory import AssistantMemoryCreate
from app.schemas.assistant_memory_embedding import AssistantMemoryEmbeddingCreate

logger = logging.getLogger(__name__)

_tag = "EmbeddingManager"


class EmbeddingManager:
    def __init__(self, api_key: str, model="text-embedding-3-small"):
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
        )
        self.model = model

    async def get_embedding(self, text) -> list[float]:
        try:
            text = text.replace("\n", " ")
            response = await self.client.embeddings.create(input=[text], model=self.model)
            return response.data[0].embedding
        except openai.OpenAIError as e:
            logger.error(f"{_tag} Error generating embedding: {e}")
            raise

    async def save_memory(
        self,
        db: AsyncSession,
        assistant_id: str,
        obj_in: AssistantMemoryCreate,
    ) -> models.AssistantMemory:
        """Save assistant memory and its embedding to the database."""
        try:
            obj_in_memory = obj_in
            assistant_memory = await crud.assistant_memory.create_with_assistant(
                db=db,
                obj_in=obj_in_memory,
            )

            logger.debug(f"{_tag} save_memory: assistant_id:{assistant_id}, obj_in_memory:{obj_in_memory}")
            embedding = await self.get_embedding(obj_in.content)
            obj_in_embedding = AssistantMemoryEmbeddingCreate(
                assistant_memory_id=assistant_memory.id,
                assistant_id=assistant_id,
                embedding=embedding,
            )

            await crud.assistant_memory_embedding.create_with_memory(db=db, obj_in=obj_in_embedding)
            return assistant_memory
        except Exception as e:
            logger.error(f"{_tag} Error saving memory and embedding: {e}")
            raise

    async def retrieve_relevant_memories(
        self,
        db: AsyncSession,
        assistant_id: str,
        query: str,
        limit: int = 5,
    ) -> schemas.RelevantMemoriesResponse:
        """
        Retrieve relevant memories based on a query.
        Returns a list of tuples containing the AssistantMemory and its similarity score.
        """
        try:
            logger.debug(f"{_tag} retrieve_relevant_memories: assistant_id:{assistant_id}")
            # Get the embedding for the query
            query_embedding = await self.get_embedding(query)

            # Fetch all memory embeddings for the assistant
            memory_embeddings = await crud.assistant_memory_embedding.get_embeddings_by_assistant(db, assistant_id)

            # Calculate cosine similarity
            def cosine_similarity(v1, v2):
                norm_v1 = np.linalg.norm(v1)
                norm_v2 = np.linalg.norm(v2)
                if norm_v1 == 0 or norm_v2 == 0:
                    return 0.0
                return np.dot(v1, v2) / (norm_v1 * norm_v2)

            # Calculate similarities and sort
            similarities = [
                (memory_id, cosine_similarity(query_embedding, np.array(embedding)))
                for memory_id, embedding in memory_embeddings
            ]
            logger.info(f"similarities: {similarities}")
            SIMILARITY_THRESHOLD = 0.05
            threshold = SIMILARITY_THRESHOLD
            # Filter out similarities below the threshold
            filtered_similarities = [s for s in similarities if s[1] >= threshold]
            # Sort the filtered similarities
            sorted_similarities = sorted(filtered_similarities, key=lambda x: x[1], reverse=True)[:limit]

            # Fetch the actual memory objects
            memory_ids = [memory_id for memory_id, _ in sorted_similarities]
            logger.debug(f"{_tag} memory_ids:{len(memory_ids)}")
            memories = await crud.assistant_memory.get_memories_by_ids(db, memory_ids)

            # Create a dictionary for quick lookup
            memory_dict = {memory.id: memory for memory in memories}

            # Return memories with their similarity scores
            # list[tuple[models.AssistantMemory, float]]
            res = [(memory_dict[memory_id], similarity) for memory_id, similarity in sorted_similarities]
            return self.convert_memory_tuples_to_pydantic(res)

        except Exception as e:
            logger.error(f"{_tag} Error retrieving relevant memories: {e}")
            raise

    def convert_memory_tuples_to_pydantic(
        self, memory_tuples: list[tuple[models.AssistantMemory, float]]
    ) -> schemas.RelevantMemoriesResponse:
        """
        Convert a list of (memory, similarity) tuples to RelevantMemoriesResponse

        Args:
            memory_tuples: List of tuples containing (AssistantMemory, similarity_score)

        Returns:
            RelevantMemoriesResponse object containing the formatted data
        """
        relevant_memories = []

        for memory, similarity in memory_tuples:
            # Convert each memory tuple to RelevantMemory
            relevant_memory = schemas.RelevantMemory(
                id=memory.id,
                assistant_id=memory.assistant_id,
                content=memory.content,
                metadata=memory.metadata,
                created_at=memory.created_at,
                updated_at=memory.updated_at,
                similarity_score=similarity,
            )
            relevant_memories.append(relevant_memory)

        return schemas.RelevantMemoriesResponse(memories=relevant_memories, total_count=len(relevant_memories))
