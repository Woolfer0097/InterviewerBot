import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import Config
from bot.db.engine import create_engine, create_sessionmaker
from bot.handlers import start, today, stats, answer, reset, export
from bot.scheduler import setup_scheduler
from bot.middleware import DatabaseMiddleware, WhitelistMiddleware
from bot.logging import logger
from sqlalchemy.exc import OperationalError
from sqlalchemy import text


async def wait_for_db(engine, max_retries: int = 30, retry_delay: float = 2.0):
    """
    Ожидает готовности БД с повторными попытками подключения.
    
    Args:
        engine: SQLAlchemy engine
        max_retries: Максимальное количество попыток
        retry_delay: Задержка между попытками в секундах
    """
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return
        except OperationalError as e:
            error_str = str(e).lower()
            # Проверяем на ошибки аутентификации
            if "password authentication failed" in error_str or "authentication failed" in error_str:
                logger.error(
                    "Database authentication failed! This usually happens when:\n"
                    "1. PostgreSQL volume exists with different credentials\n"
                    "2. POSTGRES_USER/POSTGRES_PASSWORD in docker-compose.yml don't match DATABASE_URL in .env\n\n"
                    "Solution:\n"
                    "1. Check that credentials in docker-compose.yml match DATABASE_URL in .env\n"
                    "2. If problem persists, you may need to recreate the volume:\n"
                    "   docker compose down\n"
                    "   docker volume rm interviewbot_postgres_data  # WARNING: This deletes all data!\n"
                    "   docker compose up -d\n"
                )
                raise RuntimeError(
                    "Database authentication failed. Please check credentials in docker-compose.yml and .env file. "
                    "They must match exactly."
                ) from e
            
            if attempt < max_retries - 1:
                logger.warning(f"Database not ready, attempt {attempt + 1}/{max_retries}: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection error, attempt {attempt + 1}/{max_retries}: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                raise


async def main():
    """Главная функция запуска бота."""
    # Загружаем конфигурацию
    config = Config.from_env()
    
    if not config.bot_token:
        logger.error("BOT_TOKEN not set in environment")
        sys.exit(1)
    
    # Инициализируем БД
    logger.info("Initializing database connection...")
    engine = create_engine(config)
    
    # Ждем готовности БД
    await wait_for_db(engine)
    
    sessionmaker = create_sessionmaker(engine)
    
    # Инициализируем бота и диспетчер
    bot = Bot(token=config.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Добавляем whitelist middleware (должен быть первым)
    whitelist_middleware = WhitelistMiddleware(config.whitelist)
    if whitelist_middleware.enabled:
        dp.message.middleware(whitelist_middleware)
        dp.callback_query.middleware(whitelist_middleware)
        logger.info(f"Whitelist enabled with {len(config.whitelist)} users")
    else:
        logger.info("Whitelist disabled (empty or not set)")
    
    # Добавляем middleware для сессий БД, bot и config
    db_middleware = DatabaseMiddleware(sessionmaker, bot, config)
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)
    
    # Регистрируем роутеры
    dp.include_router(start.router)
    dp.include_router(today.router)
    dp.include_router(stats.router)
    dp.include_router(answer.router)
    dp.include_router(reset.router)
    dp.include_router(export.router)
    
    # Настраиваем scheduler
    scheduler = setup_scheduler(sessionmaker, bot, config)
    scheduler.start()
    logger.info(f"Scheduler started, daily job at {config.daily_hour}:{config.daily_minute:02d} {config.tz}")
    
    try:
        # Запускаем polling
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

