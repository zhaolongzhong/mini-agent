import logging

from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api import deps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=schemas.AssistantMemoryEmbedding)
async def create_assistant_memory_embedding(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    obj_in: schemas.AssistantMemoryEmbeddingCreate,
):
    """
    Create new assistant memory embedding.
    """
    assistant_memory_embedding = await crud.assistant_memory_embedding.create_with_memory(db=db, obj_in=obj_in)
    return assistant_memory_embedding


@router.get("/{assistant_memory_id}", response_model=schemas.AssistantMemoryEmbedding)
async def read_assistant_memory_embedding(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    assistant_memory_id: str,
):
    """
    Get assistant memory embedding by memory ID.
    """
    assistant_memory_embedding = await crud.assistant_memory_embedding.get_by_memory_id(
        db=db, assistant_memory_id=assistant_memory_id
    )
    if not assistant_memory_embedding:
        raise HTTPException(status_code=404, detail="Assistant memory embedding not found")
    return assistant_memory_embedding


@router.put("/{assistant_memory_id}", response_model=schemas.AssistantMemoryEmbedding)
async def update_assistant_memory_embedding(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    assistant_memory_id: str,
    obj_in: schemas.AssistantMemoryEmbeddingUpdate,
):
    """
    Update assistant memory embedding.
    """
    assistant_memory_embedding = await crud.assistant_memory_embedding.get_by_memory_id(
        db=db, assistant_memory_id=assistant_memory_id
    )
    if not assistant_memory_embedding:
        raise HTTPException(status_code=404, detail="Assistant memory embedding not found")
    assistant_memory_embedding = await crud.assistant_memory_embedding.update(
        db=db, db_obj=assistant_memory_embedding, obj_in=obj_in
    )
    return assistant_memory_embedding


@router.delete("/{assistant_memory_id}")
async def delete_assistant_memory_embedding(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    assistant_memory_id: str,
):
    """
    Delete assistant memory embedding.
    """
    assistant_memory_embedding = await crud.assistant_memory_embedding.get_by_memory_id(
        db=db, assistant_memory_id=assistant_memory_id
    )
    if not assistant_memory_embedding:
        raise HTTPException(status_code=404, detail="Assistant memory embedding not found")
    await crud.assistant_memory_embedding.remove(db=db, id=assistant_memory_embedding.id)
    return {"success": True}
