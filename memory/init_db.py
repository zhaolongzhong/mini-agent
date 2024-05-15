from memory.database import create_all_tables
import asyncio


async def main():
    await create_all_tables()


if __name__ == "__main__":
    """Initialize the database.
    python3 -m memory.init_db
    """
    asyncio.run(main())
    print("Messages table created.")
