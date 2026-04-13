from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import settings


engine_kwargs = {"echo": False, "future": True}

if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

async_engine = create_async_engine(settings.async_database_url, **engine_kwargs)
SessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
