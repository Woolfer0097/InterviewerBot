from typing import Optional, List
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from bot.db.models import User, Question, UserQuestion, UserState


async def get_or_create_user(session: AsyncSession, tg_user_id: int) -> User:
    """Получает или создает пользователя."""
    stmt = select(User).where(User.tg_user_id == tg_user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        user = User(tg_user_id=tg_user_id, is_active=True)
        session.add(user)
        await session.flush()
        
        # Создаем user_state
        user_state = UserState(user_id=user.id, awaiting_question_id=None)
        session.add(user_state)
        await session.flush()
    
    return user


async def get_stats(session: AsyncSession, user_id: int) -> dict:
    """Возвращает статистику пользователя."""
    answered_count = await session.scalar(
        select(func.count(UserQuestion.id))
        .where(and_(UserQuestion.user_id == user_id, UserQuestion.status == "answered"))
    )
    
    sent_count = await session.scalar(
        select(func.count(UserQuestion.id))
        .where(and_(UserQuestion.user_id == user_id, UserQuestion.status == "sent"))
    )
    
    total_questions = await session.scalar(select(func.count(Question.id)))
    remaining = total_questions - (answered_count or 0)
    
    return {
        "answered": answered_count or 0,
        "sent": sent_count or 0,
        "remaining": max(0, remaining),
    }


async def select_next_questions(
    session: AsyncSession,
    user_id: int,
    high_n: int,
    low_n: int,
    total_n: int,
    threshold: int,
) -> list[Question]:
    """
    Выбирает вопросы для пользователя.
    Возвращает high_n вопросов с freq_score > threshold и low_n с <= threshold,
    всего total_n вопросов (с добором при нехватке).
    """
    # Получаем ID вопросов, на которые уже отвечено
    answered_stmt = select(UserQuestion.question_id).where(
        and_(UserQuestion.user_id == user_id, UserQuestion.status == "answered")
    )
    answered_result = await session.execute(answered_stmt)
    answered_ids = {row[0] for row in answered_result.all()}
    
    # Формируем базовое условие исключения отвеченных
    base_condition = ~Question.id.in_(answered_ids) if answered_ids else True
    
    # Выбираем high вопросы (freq_score > threshold)
    high_stmt = (
        select(Question)
        .where(and_(base_condition, Question.freq_score > threshold))
        .order_by(Question.freq_score.desc(), Question.id.asc())
        .limit(high_n)
    )
    high_result = await session.execute(high_stmt)
    high_questions = list(high_result.scalars().all())
    
    # Выбираем low вопросы (freq_score <= threshold)
    low_stmt = (
        select(Question)
        .where(and_(base_condition, Question.freq_score <= threshold))
        .order_by(Question.freq_score.desc(), Question.id.asc())
        .limit(low_n)
    )
    low_result = await session.execute(low_stmt)
    low_questions = list(low_result.scalars().all())
    
    # Собираем результат: сначала high, потом low
    selected_ids = {q.id for q in high_questions}
    result = high_questions.copy()
    
    for q in low_questions:
        if q.id not in selected_ids:
            result.append(q)
            selected_ids.add(q.id)
    
    # Если не хватает, добираем из оставшихся (любые, не отвеченные)
    if len(result) < total_n:
        remaining_ids = answered_ids | selected_ids
        remaining_condition = ~Question.id.in_(remaining_ids) if remaining_ids else True
        remaining_stmt = (
            select(Question)
            .where(remaining_condition)
            .order_by(Question.freq_score.desc(), Question.id.asc())
            .limit(total_n - len(result))
        )
        remaining_result = await session.execute(remaining_stmt)
        for q in remaining_result.scalars().all():
            if q.id not in selected_ids:
                result.append(q)
                selected_ids.add(q.id)
    
    return result[:total_n]


async def mark_sent(session: AsyncSession, user_id: int, question_ids: list[int]) -> None:
    """Помечает вопросы как отправленные."""
    for question_id in question_ids:
        stmt = select(UserQuestion).where(
            and_(UserQuestion.user_id == user_id, UserQuestion.question_id == question_id)
        )
        result = await session.execute(stmt)
        uq = result.scalar_one_or_none()
        
        if uq is None:
            uq = UserQuestion(
                user_id=user_id,
                question_id=question_id,
                status="sent",
            )
            session.add(uq)
        else:
            uq.status = "sent"
    
    await session.flush()


async def set_awaiting(session: AsyncSession, user_id: int, question_id: Optional[int]) -> None:
    """Устанавливает awaiting_question_id для пользователя."""
    stmt = select(UserState).where(UserState.user_id == user_id)
    result = await session.execute(stmt)
    state = result.scalar_one_or_none()
    
    if state is None:
        state = UserState(user_id=user_id, awaiting_question_id=question_id)
        session.add(state)
    else:
        state.awaiting_question_id = question_id
    
    await session.flush()


async def get_awaiting(session: AsyncSession, user_id: int) -> Optional[int]:
    """Получает awaiting_question_id для пользователя."""
    stmt = select(UserState).where(UserState.user_id == user_id)
    result = await session.execute(stmt)
    state = result.scalar_one_or_none()
    return state.awaiting_question_id if state else None


async def save_answer(
    session: AsyncSession,
    user_id: int,
    question_id: int,
    text: str,
) -> None:
    """Сохраняет ответ пользователя."""
    from datetime import datetime, timezone
    
    stmt = select(UserQuestion).where(
        and_(UserQuestion.user_id == user_id, UserQuestion.question_id == question_id)
    )
    result = await session.execute(stmt)
    uq = result.scalar_one_or_none()
    
    if uq is None:
        uq = UserQuestion(
            user_id=user_id,
            question_id=question_id,
            status="answered",
            answer_text=text,
            answered_at=datetime.now(timezone.utc),
        )
        session.add(uq)
    else:
        uq.status = "answered"
        uq.answer_text = text
        uq.answered_at = datetime.now(timezone.utc)
    
    # Сбрасываем awaiting
    await set_awaiting(session, user_id, None)
    await session.flush()


async def get_active_users(session: AsyncSession) -> list[User]:
    """Получает всех активных пользователей."""
    stmt = select(User).where(User.is_active == True)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def set_pending_questions(session: AsyncSession, user_id: int, question_ids: List[int]) -> None:
    """Устанавливает очередь вопросов для пользователя."""
    stmt = select(UserState).where(UserState.user_id == user_id)
    result = await session.execute(stmt)
    state = result.scalar_one_or_none()
    
    if state is None:
        state = UserState(user_id=user_id, pending_question_ids=question_ids)
        session.add(state)
    else:
        state.pending_question_ids = question_ids
    
    await session.flush()


async def get_pending_questions(session: AsyncSession, user_id: int) -> List[int]:
    """Получает очередь вопросов для пользователя."""
    stmt = select(UserState).where(UserState.user_id == user_id)
    result = await session.execute(stmt)
    state = result.scalar_one_or_none()
    return state.pending_question_ids if state and state.pending_question_ids else []


async def pop_next_question(session: AsyncSession, user_id: int) -> Optional[int]:
    """Извлекает следующий вопрос из очереди."""
    stmt = select(UserState).where(UserState.user_id == user_id)
    result = await session.execute(stmt)
    state = result.scalar_one_or_none()
    
    if not state or not state.pending_question_ids:
        return None
    
    question_id = state.pending_question_ids.pop(0)
    if not state.pending_question_ids:
        state.pending_question_ids = None
    
    await session.flush()
    return question_id


async def save_feedback(
    session: AsyncSession,
    user_id: int,
    question_id: int,
    feedback_text: str,
) -> None:
    """Сохраняет фидбек ИИ на ответ пользователя."""
    stmt = select(UserQuestion).where(
        and_(UserQuestion.user_id == user_id, UserQuestion.question_id == question_id)
    )
    result = await session.execute(stmt)
    uq = result.scalar_one_or_none()
    
    if uq is not None:
        uq.feedback_text = feedback_text
        await session.flush()


async def save_hint(
    session: AsyncSession,
    user_id: int,
    question_id: int,
    hint_text: str,
) -> None:
    """Сохраняет подсказку ИИ для вопроса."""
    stmt = select(UserQuestion).where(
        and_(UserQuestion.user_id == user_id, UserQuestion.question_id == question_id)
    )
    result = await session.execute(stmt)
    uq = result.scalar_one_or_none()
    
    if uq is None:
        # Создаем запись если её нет
        uq = UserQuestion(
            user_id=user_id,
            question_id=question_id,
            status="sent",
            hint_text=hint_text,
        )
        session.add(uq)
    else:
        uq.hint_text = hint_text
    
    await session.flush()


async def get_user_questions_with_answers(
    session: AsyncSession,
    user_id: int,
) -> list[UserQuestion]:
    """Получает все вопросы пользователя с ответами и AI данными."""
    stmt = (
        select(UserQuestion)
        .where(UserQuestion.user_id == user_id)
        .where(UserQuestion.status == "answered")
        .options(selectinload(UserQuestion.question))
        .order_by(UserQuestion.answered_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())

