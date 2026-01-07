from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram import Bot
from bot.db.dao import (
    get_or_create_user,
    mark_sent,
    set_pending_questions,
    pop_next_question,
    set_awaiting,
)
from bot.db.models import Question
from bot.services.selection import select_questions_for_user
from bot.config import Config
from bot.keyboards.inline import get_answer_keyboard


async def send_daily(session: AsyncSession, bot: Bot, tg_user_id: int, config: Config) -> None:
    """Отправляет ежедневную подборку вопросов пользователю (только первый вопрос)."""
    user = await get_or_create_user(session, tg_user_id)
    
    questions = await select_questions_for_user(session, user.id, config)
    
    if not questions:
        await bot.send_message(
            tg_user_id,
            "На сегодня все вопросы закончились! 🎉"
        )
        return
    
    # Помечаем как отправленные
    question_ids = [q.id for q in questions]
    await mark_sent(session, user.id, question_ids)
    
    # Сохраняем все вопросы в очередь (включая первый)
    await set_pending_questions(session, user.id, question_ids)
    
    # Отправляем только первый вопрос и сразу устанавливаем ожидание ответа
    first_question = questions[0]
    await set_awaiting(session, user.id, first_question.id)
    keyboard = get_answer_keyboard(first_question.id)
    await bot.send_message(
        tg_user_id,
        f"❓ {first_question.question}\n\n📊 Частота: {first_question.freq_score}/9\n\n💬 Напиши ответ текстом:",
        reply_markup=keyboard,
    )


async def send_next_question(session: AsyncSession, bot: Bot, tg_user_id: int) -> bool:
    """
    Отправляет следующий вопрос из очереди пользователю и сразу устанавливает ожидание ответа.
    Возвращает True если вопрос отправлен, False если очередь пуста.
    """
    user = await get_or_create_user(session, tg_user_id)
    
    # Получаем следующий вопрос из очереди
    question_id = await pop_next_question(session, user.id)
    
    if question_id is None:
        return False
    
    # Получаем вопрос из БД
    stmt = select(Question).where(Question.id == question_id)
    result = await session.execute(stmt)
    question = result.scalar_one_or_none()
    
    if question is None:
        # Если вопрос не найден, пробуем следующий
        return await send_next_question(session, bot, tg_user_id)
    
    # Устанавливаем ожидание ответа
    await set_awaiting(session, user.id, question.id)
    
    keyboard = get_answer_keyboard(question.id)
    await bot.send_message(
        tg_user_id,
        f"❓ {question.question}\n\n📊 Частота: {question.freq_score}/9\n\n💬 Напиши ответ текстом:",
        reply_markup=keyboard,
    )
    
    return True

