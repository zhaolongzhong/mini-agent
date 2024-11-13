import logging
from typing import Any

from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas

from .. import deps

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{conversation_id}/messages", response_model=list[schemas.Message])
async def get_messages_by_conversation_id(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    conversation_id: str,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get messages by conversation id.
    """
    messages = await crud.message.get_multi_by_conversation_id_desc(
        db=db, conversation_id=conversation_id, skip=skip, limit=limit
    )
    return messages or []


@router.get("/", response_model=list[schemas.Conversation])
async def read_conversations(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    Retrieve conversations.
    """
    conversations = await crud.conversation.get_multi_by_author(db=db, skip=skip, limit=limit)
    return conversations


@router.post("/", response_model=schemas.Conversation)
async def create_conversation(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    obj_in: schemas.ConversationCreate,
) -> Any:
    """
    Create new conversation.
    """
    obj_in.title = obj_in.title.lower()
    existing_obj = await crud.conversation.get_by_title(db=db, title=obj_in.title)
    if existing_obj:
        return existing_obj
    conversation = await crud.conversation.create_with_id(db=db, obj_in=obj_in)
    return conversation


@router.put("/{conversation_id}", response_model=schemas.Conversation)
async def update_conversation(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    conversation_id: str,
    conversation_in: schemas.ConversationUpdate,
) -> Any:
    """
    Update a conversation.
    """
    conversation = await crud.conversation.get(db=db, id=conversation_id)
    updated_obj = await crud.conversation.update(db=db, db_obj=conversation, obj_in=conversation_in)
    return updated_obj


@router.get("/{conversation_id}", response_model=schemas.Conversation)
async def read_conversation(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    conversation_id: str,
) -> Any:
    """
    Get conversation by ID.
    """
    conversation = await crud.conversation.get(db=db, id=conversation_id)
    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    conversation_id: str,
) -> Any:
    """
    Delete a conversation.
    """
    try:
        await crud.conversation.remove(db=db, id=conversation_id)
        return {"success": True}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
