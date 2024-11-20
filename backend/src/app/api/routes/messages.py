import logging
from typing import Any

from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas

from .. import deps

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[schemas.Message])
async def read_messages(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    Retrieve messages.
    """
    messages = await crud.message.get_multi(db=db, skip=skip, limit=limit)
    return messages


@router.post("", response_model=schemas.Message)
async def create_message(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    obj_in: schemas.MessageCreate,
) -> Any:
    """
    Create new message.
    """
    if not obj_in.conversation_id:
        existing_obj = await crud.conversation.get_by_title(db=db, title="default")
        if existing_obj:
            obj_in.conversation_id = existing_obj.id
        else:
            conversation = await crud.conversation.create_with_id(
                db=db, obj_in=schemas.ConversationCreate(title="default")
            )
            obj_in.conversation_id = conversation.id
    message = await crud.message.create_with_id(db=db, obj_in=obj_in)
    return message


@router.put("/{message_id}", response_model=schemas.Message)
async def update_message(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    message_id: str,
    message_in: schemas.MessageUpdate,
) -> Any:
    """
    Update a message.
    """
    message = await crud.message.get(db=db, id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    updated_obj = await crud.message.update(db=db, db_obj=message, obj_in=message_in)
    return updated_obj


@router.get("/{message_id}", response_model=schemas.Message)
async def read_message(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    message_id: str,
) -> Any:
    """
    Get message by ID.
    """
    message = await crud.message.get(db=db, id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.delete("/{message_id}")
async def delete_message(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    message_id: str,
) -> Any:
    """
    Delete a message.
    """
    try:
        message = await crud.message.get(db=db, id=message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        await crud.message.remove(db=db, id=message_id)
        return {"success": True}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
