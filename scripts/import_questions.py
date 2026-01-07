#!/usr/bin/env python3
"""Скрипт импорта вопросов из CSV файла."""
import asyncio
import csv
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.config import Config
from bot.db.engine import create_engine, create_sessionmaker
from bot.db.models import Question
from bot.utils.hashing import sha256_hash
from bot.logging import logger


async def import_questions(csv_path: str):
    """Импортирует вопросы из CSV файла."""
    config = Config.from_env()
    engine = create_engine(config)
    sessionmaker = create_sessionmaker(engine)
    
    async with sessionmaker() as session:
        imported = 0
        updated = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Проверяем наличие нужных колонок
            if 'Вопрос' not in reader.fieldnames:
                # Пробуем найти колонку с вопросом
                question_col = None
                freq_col = None
                for col in reader.fieldnames:
                    if 'вопрос' in col.lower() or 'question' in col.lower():
                        question_col = col
                    if 'часто' in col.lower() or 'балл' in col.lower() or 'freq' in col.lower():
                        freq_col = col
                
                if not question_col or not freq_col:
                    logger.error("CSV должен содержать колонки с вопросом и частотой")
                    return
            else:
                question_col = 'Вопрос'
                freq_col = 'Как часто спрашивают(балл от 1 до 10)'
            
            for row in reader:
                try:
                    # Парсим freq_score (в CSV 1-10, приводим к 0-9)
                    freq_score_raw = int(row[freq_col].strip())
                    freq_score = max(0, min(9, freq_score_raw - 1))  # 1-10 -> 0-9
                    
                    # Нормализуем вопрос
                    question_text = row[question_col].strip()
                    if not question_text:
                        continue
                    
                    # Вычисляем hash
                    question_hash = sha256_hash(question_text)
                    
                    # Проверяем существование
                    stmt = select(Question).where(Question.question_hash == question_hash)
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        # Обновляем существующий
                        existing.freq_score = freq_score
                        existing.question = question_text
                        updated += 1
                    else:
                        # Создаем новый
                        question = Question(
                            freq_score=freq_score,
                            question=question_text,
                            question_hash=question_hash,
                        )
                        session.add(question)
                        imported += 1
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Ошибка при обработке строки: {e}, строка: {row}")
                    continue
        
        await session.commit()
        logger.info(f"Импорт завершен: добавлено {imported}, обновлено {updated}")
    
    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python scripts/import_questions.py /path/to/questions.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    asyncio.run(import_questions(csv_path))

