from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.dao import select_next_questions
from bot.config import Config


async def select_questions_for_user(
    session: AsyncSession,
    user_id: int,
    config: Config,
) -> list:
    """
    Выбирает вопросы для пользователя по правилам:
    - 4 вопроса с freq_score > threshold
    - 1 вопрос с freq_score <= threshold
    - Всего config.questions_per_day вопросов
    - При нехватке добирает из другой категории
    """
    high_n = 4
    low_n = 1
    total_n = config.questions_per_day
    
    # Вычисляем сколько high и low нужно
    # Если questions_per_day != 5, пропорционально распределяем
    if total_n != 5:
        high_n = int(total_n * 0.8)  # ~80% high
        low_n = total_n - high_n
    
    questions = await select_next_questions(
        session=session,
        user_id=user_id,
        high_n=high_n,
        low_n=low_n,
        total_n=total_n,
        threshold=config.high_score_threshold,
    )
    
    return questions

