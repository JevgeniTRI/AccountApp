import asyncio

from app.db.base import Base
from app.db.session import async_engine
from app import models  # noqa: F401


async def init_db() -> None:
    try:
        async with async_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
