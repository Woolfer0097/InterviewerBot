import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import Config
from bot.db.engine import create_engine, create_sessionmaker
from bot.handlers import start, today, stats, answer, reset
from bot.scheduler import setup_scheduler
from bot.middleware import DatabaseMiddleware, WhitelistMiddleware
from bot.logging import logger


async def main():
    """Главная функция запуска бота."""
    # Загружаем конфигурацию
    config = Config.from_env()
    
    if not config.bot_token:
        logger.error("BOT_TOKEN not set in environment")
        sys.exit(1)
    
    # Инициализируем БД
    engine = create_engine(config)
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

