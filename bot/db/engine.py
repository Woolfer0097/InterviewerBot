from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.config import Config
from bot.db.models import Base


def create_engine(config: Config):
    """Создает async engine для БД."""
    return create_async_engine(
        config.database_url,
        echo=False,
        future=True,
    )


def create_sessionmaker(engine):
    """Создает async sessionmaker."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def init_db(engine):
    """Инициализирует БД (создает таблицы)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

