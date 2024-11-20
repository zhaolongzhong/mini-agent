import logging
from typing import List, Union, Optional, Annotated

from fastapi import Path, Query, Depends, APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api import deps
from app.embedding_manager import EmbeddingManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router for memory-related endpoints
router = APIRouter()

# Create a sub-router for memory operations
memory_router = APIRouter(
    prefix="/memories",  # This will be combined with the assistant_id prefix
)


@memory_router.post("", response_model=schemas.AssistantMemory)
async def create_assistant_memory(
    *,
    assistant_id: Annotated[str, Path(...)],
    db: AsyncSession = Depends(deps.get_async_db),
    obj_in: schemas.AssistantMemoryCreate,
    embedding_manager: EmbeddingManager = Depends(deps.get_embedding_manager),
):
    """Create new assistant memory."""
    # Override the assistant_id from the path
    obj_in.assistant_id = assistant_id
    assistant_memory = await embedding_manager.save_memory(db, assistant_id, obj_in)
    return assistant_memory


@memory_router.get("/{memory_id}", response_model=Optional[schemas.AssistantMemory])
async def read_assistant_memory(
    *,
    assistant_id: Annotated[str, Path(...)],
    memory_id: str = Path(...),
    db: AsyncSession = Depends(deps.get_async_db),
):
    """Get assistant memory by ID."""
    assistant_memory = await crud.assistant_memory.get(db=db, id=memory_id)
    if assistant_memory and assistant_memory.assistant_id != assistant_id:
        raise HTTPException(status_code=404, detail="Memory not found for this assistant")
    return assistant_memory


@memory_router.get("", response_model=Union[List[schemas.AssistantMemory] | schemas.RelevantMemoriesResponse])
async def list_assistant_memories(
    *,
    assistant_id: Annotated[str, Path(...)],
    db: AsyncSession = Depends(deps.get_async_db),
    embedding_manager: EmbeddingManager = Depends(deps.get_embedding_manager),
    query: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """Retrieve assistant memories."""
    if query:
        # Search by query using the embedding manager
        memories_with_similarity_scores = await embedding_manager.retrieve_relevant_memories(
            db=db, assistant_id=assistant_id, query=query, limit=limit
        )
        if not memories_with_similarity_scores:
            raise HTTPException(status_code=404, detail="No matching assistant memories found")
        return memories_with_similarity_scores
    else:
        assistant_memories = await crud.assistant_memory.get_multi_by_assistant(
            db=db, assistant_id=assistant_id, skip=skip, limit=limit
        )
        return assistant_memories


@memory_router.put("/{memory_id}", response_model=schemas.AssistantMemory)
async def update_assistant_memory(
    *,
    assistant_id: Annotated[str, Path(...)],
    memory_id: str = Path(...),
    db: AsyncSession = Depends(deps.get_async_db),
    obj_in: schemas.AssistantMemoryUpdate,
):
    """Update assistant memory."""
    assistant_memory = await crud.assistant_memory.get(db=db, id=memory_id)
    if assistant_memory.assistant_id != assistant_id:
        raise HTTPException(status_code=404, detail="Memory not found for this assistant")
    assistant_memory = await crud.assistant_memory.update(db=db, db_obj=assistant_memory, obj_in=obj_in)
    return assistant_memory


@memory_router.delete("")
async def delete_assistant_memories(
    *,
    assistant_id: Annotated[str, Path(...)],
    delete_request: schemas.AssistantMemoryBulkDeleteRequest,
    db: AsyncSession = Depends(deps.get_async_db),
):
    """Bulk delete assistant memories."""
    # Validate all memories exist and belong to the assistant
    failed_ids = []
    success_ids = []

    for memory_id in delete_request.memory_ids:
        try:
            memory = await crud.assistant_memory.get(db=db, id=memory_id)
            if not memory:
                failed_ids.append({"id": memory_id, "reason": "Memory not found"})
                continue

            if memory.assistant_id != assistant_id:
                failed_ids.append({"id": memory_id, "reason": "Memory does not belong to this assistant"})
                continue

            await crud.assistant_memory.remove(db=db, id=memory_id)
            success_ids.append(memory_id)

        except Exception as e:
            failed_ids.append({"id": memory_id, "reason": str(e)})

    return {
        "success": len(failed_ids) == 0,
        "deleted_count": len(success_ids),
        "successful_deletions": success_ids,
        "failed_deletions": failed_ids,
    }


@memory_router.delete("/{memory_id}")
async def delete_assistant_memory(
    *,
    assistant_id: Annotated[str, Path(...)],
    memory_id: str = Path(...),
    db: AsyncSession = Depends(deps.get_async_db),
):
    """Delete assistant memory."""
    assistant_memory = await crud.assistant_memory.get(id=memory_id)
    if assistant_memory.assistant_id != assistant_id:
        raise HTTPException(status_code=404, detail="Memory not found for this assistant")
    try:
        await crud.assistant_memory.remove(db=db, id=memory_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


async def validate_assistant(
    assistant_id: Annotated[str, Path(...)],
) -> str:
    if not assistant_id:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return assistant_id


router.include_router(memory_router, prefix="/{assistant_id}", dependencies=[Depends(validate_assistant)])
