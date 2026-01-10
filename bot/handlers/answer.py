from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram import Bot
from bot.db.dao import (
    get_or_create_user,
    set_awaiting,
    get_awaiting,
    save_answer,
    get_pending_questions,
    set_pending_questions,
)
from bot.db.models import Question, UserQuestion
from bot.services.delivery import send_next_question
from bot.services.hint import generate_hint, generate_feedback
from bot.keyboards.inline import get_feedback_keyboard, get_edit_answer_keyboard
from bot.logging import logger

router = Router()


def escape_markdown_v2(text: str) -> str:
    """
    Экранирует специальные символы MarkdownV2 для безопасной вставки в сообщения Telegram.
    
    Args:
        text: Текст для экранирования
        
    Returns:
        Экранированный текст
    """
    # ВАЖНО: Сначала экранируем обратный слэш, чтобы не экранировать уже экранированные символы
    text = text.replace('\\', '\\\\')
    
    # Затем экранируем остальные специальные символы MarkdownV2
    # Список всех зарезервированных символов в MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '{', '}', '.', '!', '|']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_hint_with_spoiler(hint_text: str) -> str:
    """
    Форматирует подсказку с правильным spoiler для MarkdownV2.
    Ищет эталонный ответ между || || или ||текст|| и правильно форматирует его.
    
    Args:
        hint_text: Текст подсказки от ИИ
        
    Returns:
        Отформатированный текст с правильным spoiler
    """
    import re
    
    # Ищем паттерн || текст || или ||текст|| (с возможными пробелами)
    # Используем нежадный поиск, чтобы найти первый spoiler
    pattern = r'\|\|\s*(.*?)\s*\|\|'
    
    def escape_spoiler_content(text: str) -> str:
        """Экранирует только | и \ внутри spoiler для MarkdownV2"""
        # ВАЖНО: Сначала экранируем обратный слэш
        text = text.replace('\\', '\\\\')
        # Затем экранируем вертикальную черту
        text = text.replace('|', '\\|')
        return text
    
    # Находим все spoiler блоки
    parts = []
    last_end = 0
    
    for match in re.finditer(pattern, hint_text, flags=re.DOTALL):
        # Добавляем текст до spoiler (подсказка)
        if match.start() > last_end:
            hint_part = hint_text[last_end:match.start()].strip()
            if hint_part:
                # Экранируем подсказку для MarkdownV2
                escaped_hint = escape_markdown_v2(hint_part)
                parts.append(escaped_hint)
        
        # Обрабатываем spoiler (эталонный ответ)
        spoiler_text = match.group(1)
        escaped_spoiler = escape_spoiler_content(spoiler_text)
        parts.append(f'||{escaped_spoiler}||')
        
        last_end = match.end()
    
    # Добавляем оставшийся текст после последнего spoiler
    if last_end < len(hint_text):
        remaining = hint_text[last_end:].strip()
        if remaining:
            escaped_remaining = escape_markdown_v2(remaining)
            parts.append(escaped_remaining)
    
    # Если spoiler не найден, просто экранируем весь текст
    if not parts:
        return escape_markdown_v2(hint_text)
    
    return '\n\n'.join(parts)


@router.callback_query(F.data.startswith("hint:"))
async def callback_hint(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Обработчик нажатия на кнопку 'Подсказка' - генерирует подсказку через ИИ."""
    question_id = int(callback.data.split(":")[1])
    tg_user_id = callback.from_user.id
    
    # Получаем вопрос из БД
    stmt = select(Question).where(Question.id == question_id)
    result = await session.execute(stmt)
    question = result.scalar_one_or_none()
    
    if question is None:
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    
    await callback.answer("Генерирую подсказку...")
    
    # Генерируем подсказку
    try:
        hint = await generate_hint(question.question, question.freq_score)
        # Форматируем подсказку с правильным spoiler для MarkdownV2
        formatted_hint = format_hint_with_spoiler(hint)
        await callback.message.answer(
            f"*Подсказка:*\n\n{formatted_hint}",
            parse_mode="MarkdownV2"
        )
    except ValueError as e:
        # Нет API ключей
        logger.warning(f"AI API key not configured: {e}")
        await callback.message.answer(
            "Подсказки недоступны: не настроен API ключ.\n\n"
            "Добавьте GEMINI_API_KEY в .env файл."
        )
    except Exception as e:
        logger.error(f"Error generating hint for question {question_id}: {e}")
        await callback.message.answer("Не удалось сгенерировать подсказку. Попробуй позже.")


@router.callback_query(F.data.startswith("feedback_no:"))
async def callback_feedback_no(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Обработчик нажатия на кнопку 'Нет' - пропускает получение фидбека."""
    question_id = int(callback.data.split(":")[1])
    tg_user_id = callback.from_user.id
    
    await callback.answer()
    
    # Отправляем следующий вопрос
    has_next = await send_next_question(session, bot, tg_user_id)
    
    if not has_next:
        await callback.message.answer("Все вопросы завершены!")


@router.callback_query(F.data.startswith("feedback:"))
async def callback_feedback(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Обработчик нажатия на кнопку 'Получить фидбек' - генерирует фидбек через ИИ."""
    question_id = int(callback.data.split(":")[1])
    tg_user_id = callback.from_user.id
    
    user = await get_or_create_user(session, tg_user_id)
    
    # Получаем вопрос и ответ из БД
    question_stmt = select(Question).where(Question.id == question_id)
    question_result = await session.execute(question_stmt)
    question = question_result.scalar_one_or_none()
    
    if question is None:
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    
    # Получаем ответ пользователя
    answer_stmt = select(UserQuestion).where(
        UserQuestion.user_id == user.id,
        UserQuestion.question_id == question_id
    )
    answer_result = await session.execute(answer_stmt)
    user_question = answer_result.scalar_one_or_none()
    
    if user_question is None or not user_question.answer_text:
        await callback.answer("Ответ не найден", show_alert=True)
        return
    
    await callback.answer("Генерирую фидбек...")
    
    # Генерируем фидбек
    try:
        feedback = await generate_feedback(
            question.question,
            user_question.answer_text,
            question.freq_score
        )
        
        keyboard = get_edit_answer_keyboard(question_id)
        # Экранируем специальные символы MarkdownV2 в AI-генерированном тексте
        escaped_feedback = escape_markdown_v2(feedback)
        await callback.message.answer(
            f"*Фидбек на твой ответ:*\n\n{escaped_feedback}",
            parse_mode="MarkdownV2",
            reply_markup=keyboard
        )
        
        # Отправляем следующий вопрос после фидбека
        has_next = await send_next_question(session, bot, tg_user_id)
        
        if not has_next:
            await callback.message.answer("Все вопросы завершены!")
    except ValueError as e:
        # Нет API ключей
        logger.warning(f"AI API key not configured: {e}")
        await callback.message.answer(
            "Фидбек недоступен: не настроен API ключ.\n\n"
            "Добавьте GEMINI_API_KEY в .env файл."
        )
        
        # Отправляем следующий вопрос даже если фидбек недоступен
        has_next = await send_next_question(session, bot, tg_user_id)
        
        if not has_next:
            await callback.message.answer("Все вопросы завершены!")
    except Exception as e:
        logger.error(f"Error generating feedback for question {question_id}: {e}")
        await callback.message.answer("Не удалось сгенерировать фидбек. Попробуй позже.")
        
        # Отправляем следующий вопрос даже если произошла ошибка
        has_next = await send_next_question(session, bot, tg_user_id)
        
        if not has_next:
            await callback.message.answer("Все вопросы завершены!")


@router.callback_query(F.data.startswith("edit:"))
async def callback_edit_answer(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Обработчик нажатия на кнопку 'Изменить ответ' - позволяет изменить ответ."""
    question_id = int(callback.data.split(":")[1])
    tg_user_id = callback.from_user.id
    
    user = await get_or_create_user(session, tg_user_id)
    
    # Устанавливаем ожидание нового ответа
    await set_awaiting(session, user.id, question_id)
    
    await callback.answer()
    await callback.message.answer("Ок, напиши исправленный ответ текстом одним сообщением")


@router.callback_query(F.data.startswith("keep:"))
async def callback_keep_answer(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Обработчик нажатия на кнопку 'Оставить ответ' - оставляет ответ без изменений."""
    question_id = int(callback.data.split(":")[1])
    tg_user_id = callback.from_user.id
    
    await callback.answer("Ответ оставлен без изменений")
    await callback.message.answer("Ответ сохранен. Продолжаем!")


@router.callback_query(F.data.startswith("menu:"))
async def callback_menu(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Обработчик нажатия на кнопку 'Меню' - отменяет текущее Ответ на вопрос."""
    question_id = int(callback.data.split(":")[1])
    tg_user_id = callback.from_user.id
    
    user = await get_or_create_user(session, tg_user_id)
    
    # Сбрасываем ожидание ответа
    await set_awaiting(session, user.id, None)
    
    await callback.answer("Ответ отменен")
    await callback.message.answer(
        "Ответ на вопрос отменен.\n\n"
        "Используй команды:\n"
        "• /today - получить вопросы\n"
        "• /stats - статистика\n"
        "• /reset_progress - сбросить прогресс"
    )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_answer(message: Message, session: AsyncSession, bot: Bot):
    """Обработчик текстового ответа пользователя."""
    tg_user_id = message.from_user.id
    
    user = await get_or_create_user(session, tg_user_id)
    awaiting_question_id = await get_awaiting(session, user.id)
    
    if awaiting_question_id is None:
        # Пользователь не ожидает ответа, игнорируем
        return
    
    answer_text = message.text.strip()
    
    if not answer_text:
        await message.answer("Ответ не может быть пустым. Попробуй еще раз.")
        return
    
    try:
        await save_answer(session, user.id, awaiting_question_id, answer_text)
        
        # Убираем текущий вопрос из очереди
        pending = await get_pending_questions(session, user.id)
        if awaiting_question_id in pending:
            pending.remove(awaiting_question_id)
            await set_pending_questions(session, user.id, pending)
        
        logger.info(f"User {tg_user_id} answered question {awaiting_question_id}")
        
        # Предлагаем получить фидбек одним сообщением
        keyboard = get_feedback_keyboard(awaiting_question_id)
        await message.answer(
            "Ответ сохранен. Хочешь получить фидбек на свой ответ?",
            reply_markup=keyboard
        )
            
    except Exception as e:
        logger.error(f"Error saving answer for user {tg_user_id}: {e}")
        await message.answer("Произошла ошибка при сохранении ответа.")
        await session.rollback()
