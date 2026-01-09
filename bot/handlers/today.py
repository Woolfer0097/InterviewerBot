from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from bot.services.delivery import send_daily
from bot.config import Config
from bot.logging import logger

router = Router()


@router.message(Command("today"))
async def cmd_today(message: Message, session: AsyncSession, bot: Bot, config: Config):
    """Обработчик команды /today - выдает 5 вопросов сейчас."""
    tg_user_id = message.from_user.id
    
    try:
        await send_daily(session, bot, tg_user_id, config)
        logger.info(f"Sent daily questions to user {tg_user_id}")
    except Exception as e:
        logger.error(f"Error sending daily questions to {tg_user_id}: {e}")
        await message.answer("Произошла ошибка при получении вопросов.")

