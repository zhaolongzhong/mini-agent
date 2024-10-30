import asyncio
import logging
import argparse

from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa
from app.database import Base, AsyncSessionLocal, async_engine

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_tables() -> None:
    Base.metadata.create_all(bind=async_engine)  # Create all tables


async def init_db(db: AsyncSession, drop_all_table: bool) -> None:
    try:
        logger.debug(f"init_db drop_all_table: {drop_all_table}")
        async with async_engine.begin() as conn:
            if drop_all_table:
                await conn.run_sync(Base.metadata.drop_all)
            # Tables should be created with Alembic migrations
            # But if you don't want to use migrations, create
            # the tables un-commenting the next line
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raise


async def init(is_testing: bool) -> None:
    async with AsyncSessionLocal() as session:
        await init_db(db=session, drop_all_table=is_testing)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the database.")
    parser.add_argument("--testing", action="store_true", help="Initialize for testing")
    args = parser.parse_args()

    logger.info("Creating initial data")
    await init(is_testing=args.testing)
    logger.info("Initial data created")


if __name__ == "__main__":
    asyncio.run(main())
