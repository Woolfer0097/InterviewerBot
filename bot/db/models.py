from datetime import datetime
from typing import List
from sqlalchemy import BigInteger, Boolean, SmallInteger, String, Text, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    freq_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    user_questions: Mapped[list["UserQuestion"]] = relationship(back_populates="question")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user_questions: Mapped[list["UserQuestion"]] = relationship(back_populates="user")
    user_state: Mapped["UserState"] = relationship(back_populates="user", uselist=False)


class UserQuestion(Base):
    __tablename__ = "user_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("questions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 'sent' | 'answered'
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI feedback на ответ
    hint_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI подсказка

    user: Mapped["User"] = relationship(back_populates="user_questions")
    question: Mapped["Question"] = relationship(back_populates="user_questions")

    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question"),
    )


class UserState(Base):
    __tablename__ = "user_state"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    awaiting_question_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pending_question_ids: Mapped[List[int] | None] = mapped_column(JSONB, nullable=True)  # Очередь вопросов

    user: Mapped["User"] = relationship(back_populates="user_state")

