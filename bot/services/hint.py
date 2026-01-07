import asyncio
from bot.utils.ai_interface import AIInterface
from bot.logging import logger


def create_hint_prompt(question: str, freq_score: int) -> str:
    """
    Создает промпт для генерации подсказки по вопросу.
    
    Args:
        question: Текст вопроса
        freq_score: Частота вопроса (0-9)
        
    Returns:
        Промпт для ИИ
    """
    prompt = f"""Ты - опытный технический интервьюер и ментор по DevOps/системному администрированию.

Вопрос для собеседования:
"{question}"

Частота вопроса: {freq_score}/9 (чем выше, тем чаще спрашивают)

Задача: Дай подсказку для подготовки к ответу на этот вопрос

Формат ответа: сначала подсказка, без префиксов типа "Подсказка:" или "Совет:". Затем в формате markdownV2 дай эталонный ответ закрытый под символами spoiler "|| ||"
"""
    
    return prompt


async def generate_hint(question: str, freq_score: int) -> str:
    """
    Генерирует подсказку для вопроса с помощью ИИ.
    
    Args:
        question: Текст вопроса
        freq_score: Частота вопроса
        
    Returns:
        Текст подсказки
    """
    try:
        # Создаем AIInterface в отдельном потоке, так как он синхронный
        loop = asyncio.get_event_loop()
        ai = await loop.run_in_executor(
            None,
            lambda: AIInterface(retry_attempts=2, retry_delay=1.0)
        )
        
        prompt = create_hint_prompt(question, freq_score)
        
        # Выполняем генерацию в отдельном потоке
        hint = await loop.run_in_executor(None, ai.generate_text, prompt)
        return hint.strip()
    except Exception as e:
        logger.error(f"Error generating hint: {e}")
        return "❌ Не удалось сгенерировать подсказку. Попробуй позже."


def create_feedback_prompt(question: str, user_answer: str, freq_score: int) -> str:
    """
    Создает промпт для генерации фидбека на ответ пользователя.
    
    Args:
        question: Текст вопроса
        user_answer: Ответ пользователя
        freq_score: Частота вопроса (0-9)
        
    Returns:
        Промпт для ИИ
    """
    prompt = f"""Ты - опытный технический интервьюер и ментор по DevOps/системному администрированию.

Вопрос для собеседования:
"{question}"

Частота вопроса: {freq_score}/9 (чем выше, тем чаще спрашивают)

Ответ кандидата:
"{user_answer}"

Задача: Дай конструктивный фидбек на ответ кандидата. Фидбек должен:
1. Оценить полноту ответа (что хорошо, что можно улучшить)
2. Указать на пропущенные важные аспекты (если есть)
3. Дать конкретные рекомендации по улучшению
4. Быть конструктивным и поддерживающим
5. Быть кратким (3-5 предложений)

Формат ответа: только фидбек, без дополнительных пояснений, без префиксов типа "Фидбек:" или "Оценка:".

Пример хорошего фидбека:
"Хорошо, что ты упомянул основные компоненты. Однако стоило бы также рассказать о разнице между CPU-bound и I/O-bound процессами и как это влияет на интерпретацию метрики. Также полезно упомянуть, что load average учитывает процессы в состоянии R (running) и D (uninterruptible sleep)."

Сгенерируй фидбек:"""
    
    return prompt


async def generate_feedback(question: str, user_answer: str, freq_score: int) -> str:
    """
    Генерирует фидбек на ответ пользователя с помощью ИИ.
    
    Args:
        question: Текст вопроса
        user_answer: Ответ пользователя
        freq_score: Частота вопроса
        
    Returns:
        Текст фидбека
    """
    try:
        # Создаем AIInterface в отдельном потоке, так как он синхронный
        loop = asyncio.get_event_loop()
        ai = await loop.run_in_executor(
            None,
            lambda: AIInterface(retry_attempts=2, retry_delay=1.0)
        )
        
        prompt = create_feedback_prompt(question, user_answer, freq_score)
        
        # Выполняем генерацию в отдельном потоке
        feedback = await loop.run_in_executor(None, ai.generate_text, prompt)
        return feedback.strip()
    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        return "❌ Не удалось сгенерировать фидбек. Попробуй позже."

