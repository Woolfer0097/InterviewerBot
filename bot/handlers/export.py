from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.dao import get_or_create_user, get_user_questions_with_answers
from bot.services.export import export_to_markdown, export_to_csv
from bot.logging import logger

router = Router()


@router.message(Command("export_md"))
async def cmd_export_markdown(message: Message, session: AsyncSession):
    """Обработчик команды /export_md - экспорт в Markdown."""
    tg_user_id = message.from_user.id
    
    try:
        user = await get_or_create_user(session, tg_user_id)
        user_questions = await get_user_questions_with_answers(session, user.id)
        
        if not user_questions:
            await message.answer("У тебя пока нет отвеченных вопросов для экспорта.")
            return
        
        # Получаем имя пользователя
        user_name = message.from_user.full_name or f"User_{tg_user_id}"
        
        # Генерируем Markdown
        md_content = export_to_markdown(user_questions, user_name)
        
        # Отправляем как файл
        filename = f"interview_{tg_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        file = BufferedInputFile(
            md_content.encode('utf-8'),
            filename=filename
        )
        
        await message.answer_document(
            file,
            caption=f"Экспорт в Markdown\nВсего вопросов: {len(user_questions)}"
        )
        
        logger.info(f"User {tg_user_id} exported {len(user_questions)} questions to Markdown")
        
    except Exception as e:
        logger.error(f"Error exporting to Markdown for user {tg_user_id}: {e}")
        await message.answer("Произошла ошибка при экспорте. Попробуй позже.")


@router.message(Command("export_csv"))
async def cmd_export_csv(message: Message, session: AsyncSession):
    """Обработчик команды /export_csv - экспорт в CSV."""
    tg_user_id = message.from_user.id
    
    try:
        user = await get_or_create_user(session, tg_user_id)
        user_questions = await get_user_questions_with_answers(session, user.id)
        
        if not user_questions:
            await message.answer("У тебя пока нет отвеченных вопросов для экспорта.")
            return
        
        # Генерируем CSV
        csv_content = export_to_csv(user_questions)
        
        # Отправляем как файл
        filename = f"interview_{tg_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file = BufferedInputFile(
            csv_content.encode('utf-8-sig'),  # UTF-8 with BOM for Excel
            filename=filename
        )
        
        await message.answer_document(
            file,
            caption=f"Экспорт в CSV\nВсего вопросов: {len(user_questions)}"
        )
        
        logger.info(f"User {tg_user_id} exported {len(user_questions)} questions to CSV")
        
    except Exception as e:
        logger.error(f"Error exporting to CSV for user {tg_user_id}: {e}")
        await message.answer("Произошла ошибка при экспорте. Попробуй позже.")


@router.callback_query(F.data.startswith("export:"))
async def callback_export(callback: CallbackQuery, session: AsyncSession):
    """Обработчик кнопок экспорта."""
    export_format = callback.data.split(":")[1]  # 'md' or 'csv'
    tg_user_id = callback.from_user.id
    
    await callback.answer("Генерирую файл...")
    
    try:
        user = await get_or_create_user(session, tg_user_id)
        user_questions = await get_user_questions_with_answers(session, user.id)
        
        if not user_questions:
            await callback.message.answer("У тебя пока нет отвеченных вопросов для экспорта.")
            return
        
        if export_format == "md":
            user_name = callback.from_user.full_name or f"User_{tg_user_id}"
            content = export_to_markdown(user_questions, user_name)
            filename = f"interview_{tg_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            file_content = content.encode('utf-8')
            caption = f"Экспорт в Markdown\nВсего вопросов: {len(user_questions)}"
        elif export_format == "csv":
            content = export_to_csv(user_questions)
            filename = f"interview_{tg_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            file_content = content.encode('utf-8-sig')
            caption = f"Экспорт в CSV\nВсего вопросов: {len(user_questions)}"
        else:
            await callback.message.answer("Неизвестный формат экспорта.")
            return
        
        file = BufferedInputFile(file_content, filename=filename)
        await callback.message.answer_document(file, caption=caption)
        
        logger.info(f"User {tg_user_id} exported {len(user_questions)} questions to {export_format.upper()}")
        
    except Exception as e:
        logger.error(f"Error exporting to {export_format} for user {tg_user_id}: {e}")
        await callback.message.answer("Произошла ошибка при экспорте. Попробуй позже.")

