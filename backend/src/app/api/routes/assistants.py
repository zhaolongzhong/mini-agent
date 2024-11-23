import logging
from typing import Any, Optional

from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas

from .. import deps

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[schemas.Assistant])
async def read_assistants(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    Retrieve assistants.
    """
    assistants = await crud.assistant.get_multi(db=db, skip=skip, limit=limit)
    return assistants


@router.post("", response_model=schemas.Assistant)
async def create_assistant(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    obj_in: schemas.AssistantCreate,
) -> Any:
    """
    Create new assistant. If assistant with same name exists, return it.
    """
    try:
        existing_assistant = await crud.assistant.get_by_name(db=db, name=obj_in.name)
        if existing_assistant:
            return existing_assistant

        if obj_in.metadata and obj_in.metadata.is_primary:
            primary = await crud.assistant.get_primary(db=db)
            if primary:
                return primary

        assistant = await crud.assistant.create_with_id(db=db, obj_in=obj_in)
        return assistant

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating assistant: {str(e)}")


@router.put("/{assistant_id}", response_model=schemas.Assistant)
async def update_assistant(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    assistant_id: str,
    assistant_in: schemas.AssistantUpdate,
) -> Any:
    """
    Update an assistant.
    """
    assistant = await crud.assistant.get(db=db, id=assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    try:
        updated_obj = await crud.assistant.update(db=db, db_obj=assistant, obj_in=assistant_in)
        return updated_obj
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating assistant: {str(e)}")


@router.get("/{assistant_id}", response_model=schemas.Assistant)
async def read_assistant(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    assistant_id: str,
) -> Any:
    """
    Get assistant by ID.
    """
    assistant = await crud.assistant.get(db=db, id=assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return assistant


@router.delete("/{assistant_id}")
async def delete_assistant(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    assistant_id: str,
) -> Any:
    """
    Delete an assistant.
    """
    try:
        assistant = await crud.assistant.get(db=db, id=assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail="Assistant not found")
        await crud.assistant.remove(db=db, id=assistant_id)
        return {"success": True}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/{assistant_id}/conversations", response_model=list[schemas.Conversation])
async def read_conversations_by_assistant_id(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    assistant_id: str,
    is_primary: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    Retrieve conversations.
    """
    conversations = await crud.conversation.get_conversations_by_assistant_id(
        db=db, assistant_id=assistant_id, is_primary=is_primary, skip=skip, limit=limit
    )
    return conversations
