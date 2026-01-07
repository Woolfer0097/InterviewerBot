from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from bot.db.dao import get_or_create_user, set_awaiting
from bot.db.models import UserQuestion, UserState
from bot.logging import logger

router = Router()


@router.message(Command("reset_progress"))
async def cmd_reset_progress(message: Message, session: AsyncSession):
    """Обработчик команды /reset_progress - сбрасывает прогресс пользователя."""
    tg_user_id = message.from_user.id
    
    user = await get_or_create_user(session, tg_user_id)
    
    # Удаляем все записи user_questions
    stmt = delete(UserQuestion).where(UserQuestion.user_id == user.id)
    await session.execute(stmt)
    
    # Сбрасываем awaiting
    await set_awaiting(session, user.id, None)
    
    await session.flush()
    
    logger.info(f"User {tg_user_id} reset progress")
    await message.answer("✅ Прогресс сброшен! Все вопросы снова доступны.")

