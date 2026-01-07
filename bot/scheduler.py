from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from aiogram import Bot
from bot.db.dao import get_active_users
from bot.services.delivery import send_daily
from bot.config import Config
from bot.logging import logger


def setup_scheduler(
    sessionmaker: async_sessionmaker[AsyncSession],
    bot: Bot,
    config: Config,
) -> AsyncIOScheduler:
    """Настраивает и возвращает scheduler с ежедневным job."""
    scheduler = AsyncIOScheduler(timezone=config.tz)
    
    async def daily_job():
        """Ежедневная рассылка вопросов всем активным пользователям."""
        async with sessionmaker() as session:
            try:
                users = await get_active_users(session)
                logger.info(f"Starting daily job for {len(users)} users")
                
                for user in users:
                    try:
                        await send_daily(session, bot, user.tg_user_id, config)
                        await session.commit()
                        logger.info(f"Sent daily questions to user {user.tg_user_id}")
                    except Exception as e:
                        logger.error(f"Error sending daily to user {user.tg_user_id}: {e}")
                        await session.rollback()
            except Exception as e:
                logger.error(f"Error in daily job: {e}")
                await session.rollback()
    
    scheduler.add_job(
        daily_job,
        trigger=CronTrigger(hour=config.daily_hour, minute=config.daily_minute),
        id="daily_questions",
        name="Daily questions delivery",
        replace_existing=True,
    )
    
    return scheduler

