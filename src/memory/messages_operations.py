import asyncio
from typing import Optional

from memory.database import Message, get_async_db
from sqlalchemy import select


class MessageOperations:
    _instance: Optional["MessageOperations"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    async def add_message(self, role, content, message_json=None):
        async with get_async_db() as db:
            new_message = Message(role=role, content=content, message_json=message_json)
            db.add(new_message)
            await db.commit()
            await db.refresh(new_message)
            return new_message

    async def get_message(self, message_id):
        async with get_async_db() as db:
            return await db.get(Message, message_id)

    async def update_message(self, message_id, content=None, message_json=None):
        async with get_async_db() as db:
            message = await db.get(Message, message_id)
            if message:
                if content:
                    message.content = content
                if message_json:
                    message.message_json = message_json
                await db.commit()
                await db.refresh(message)
            return message

    async def delete_message(self, message_id):
        async with get_async_db() as db:
            message = await db.get(Message, message_id)
            if message:
                await db.delete(message)
                await db.commit()

    async def get_latest_messages(self, limit: int) -> list[Message]:
        async with get_async_db() as db:
            result = await db.execute(select(Message).order_by(Message.created_at.desc()).limit(limit))
            return result.scalars().all()


async def main():
    message_ops = MessageOperations()
    new_message = await message_ops.add_message(role="user", content="This is a test message.")
    print(f"Added message: {new_message}")

    fetched_message = await message_ops.get_message(new_message.id)
    print(f"Fetched message: {fetched_message}")

    updated_message = await message_ops.update_message(new_message.id, content="This is an updated test message.")
    print(f"Updated message: {updated_message}")

    # delete_message(new_message.id)
    # print(f"Deleted message with ID: {new_message.id}")


if __name__ == "__main__":
    asyncio.run(main())
