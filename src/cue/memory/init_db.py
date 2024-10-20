import asyncio

from .database import create_all_tables


async def main():
    await create_all_tables()


if __name__ == "__main__":
    """Initialize the database.
    python3 -m src.cue.memory.init_db
    """
    asyncio.run(main())
    print("Messages table created.")
