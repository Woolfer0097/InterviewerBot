#!/bin/bash
# Скрипт для восстановления базы данных после миграций
# Импортирует вопросы из data.csv

set -e

echo "🔄 Восстановление базы данных..."

# Проверяем наличие файла data.csv
if [ ! -f "data.csv" ]; then
    echo "❌ Файл data.csv не найден в текущей директории"
    echo "💡 Убедитесь, что файл data.csv существует"
    exit 1
fi

echo "📦 Применение миграций..."
docker compose exec -T bot alembic upgrade head

echo "📥 Импорт вопросов из data.csv..."
docker compose exec -T bot python scripts/import_questions.py /app/data.csv

echo "✅ База данных восстановлена!"
echo "📊 Проверка количества вопросов..."

# Проверяем количество вопросов в БД
QUESTION_COUNT=$(docker compose exec -T bot python -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from bot.config import Config
from bot.db.engine import create_engine, create_sessionmaker
from bot.db.models import Question
from sqlalchemy import select

async def check():
    config = Config.from_env()
    engine = create_engine(config)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as session:
        result = await session.execute(select(Question))
        count = len(result.scalars().all())
        print(count)
    await engine.dispose()

asyncio.run(check())
" 2>/dev/null || echo "0")

if [ "$QUESTION_COUNT" -gt 0 ]; then
    echo "✅ Импортировано вопросов: $QUESTION_COUNT"
else
    echo "⚠️  Вопросы не найдены. Проверьте файл data.csv и логи выше"
fi

