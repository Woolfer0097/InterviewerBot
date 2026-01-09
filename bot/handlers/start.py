from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.dao import get_or_create_user
from bot.logging import logger

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    """Обработчик команды /start - регистрирует пользователя и включает рассылку."""
    tg_user_id = message.from_user.id
    
    user = await get_or_create_user(session, tg_user_id)
    
    logger.info(f"User {tg_user_id} registered/activated")
    
    await message.answer(
        "Привет! Я бот для подготовки к собеседованиям.\n\n"
        "Каждый день в 09:00 MSK я буду отправлять тебе 5 вопросов.\n"
        "Используй команды:\n"
        "• /today - получить вопросы сейчас\n"
        "• /stats - статистика\n"
        "• /reset_progress - сбросить прогресс"
    )

