from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.config import Config
from bot.db.models import Base


def create_engine(config: Config):
    """Создает async engine для БД."""
    return create_async_engine(
        config.database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,  # Проверяет соединения перед использованием
        pool_recycle=3600,   # Переподключается каждые 3600 секунд
        pool_size=10,        # Размер пула соединений
        max_overflow=20,     # Максимальное количество дополнительных соединений
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

