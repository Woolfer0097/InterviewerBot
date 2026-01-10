from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.dao import get_or_create_user, get_stats
from bot.keyboards.inline import get_export_keyboard
from bot.logging import logger

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Обработчик команды /stats - показывает статистику."""
    tg_user_id = message.from_user.id
    
    user = await get_or_create_user(session, tg_user_id)
    stats = await get_stats(session, user.id)
    
    text = (
        f"Статистика:\n\n"
        f"Отвечено: {stats['answered']}\n"
        f"Отправлено: {stats['sent']}\n"
        f"Осталось: {stats['remaining']}"
    )
    
    # Добавляем кнопки экспорта, если есть отвеченные вопросы
    keyboard = None
    if stats['answered'] > 0:
        keyboard = get_export_keyboard()
    
    await message.answer(text, reply_markup=keyboard)

