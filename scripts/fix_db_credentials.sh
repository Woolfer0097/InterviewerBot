#!/bin/bash
# Скрипт для исправления credentials PostgreSQL в существующем volume
# Использование: ./scripts/fix_db_credentials.sh

set -e

echo "🔧 Исправление credentials PostgreSQL..."

# Проверяем, запущен ли контейнер БД
if ! docker ps | grep -q devops_mock_db; then
    echo "❌ Контейнер БД не запущен. Запустите: docker compose up -d db"
    exit 1
fi

# Credentials из docker-compose.yml (должны совпадать с DATABASE_URL в .env)
# По умолчанию используются значения из docker-compose.yml
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
POSTGRES_DB="devops_mock"

echo "📝 Обновление пароля для пользователя: $POSTGRES_USER"
echo "📝 База данных: $POSTGRES_DB"

# Пытаемся обновить пароль (может не сработать если используется другой пароль)
echo "🔄 Попытка обновления пароля..."
if docker exec -e PGPASSWORD=postgres devops_mock_db psql -U postgres -c "ALTER USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';" 2>/dev/null; then
    echo "✅ Пароль обновлен успешно"
else
    echo "⚠️  Не удалось обновить пароль автоматически (возможно, используется другой пароль)"
    echo "💡 Попробуйте подключиться вручную:"
    echo "   docker exec -it devops_mock_db psql -U postgres"
    echo "   Затем выполните: ALTER USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';"
    echo ""
    echo "Или используйте текущий пароль для подключения и обновите его."
fi

# Проверяем существование БД
DB_EXISTS=$(docker exec -e PGPASSWORD=$POSTGRES_PASSWORD devops_mock_db psql -U $POSTGRES_USER -tAc "SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DB'")

if [ "$DB_EXISTS" != "1" ]; then
    echo "📦 Создание базы данных: $POSTGRES_DB"
    docker exec -e PGPASSWORD=$POSTGRES_PASSWORD devops_mock_db psql -U $POSTGRES_USER -c "CREATE DATABASE $POSTGRES_DB;" || true
    docker exec -e PGPASSWORD=$POSTGRES_PASSWORD devops_mock_db psql -U $POSTGRES_USER -c "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;" || true
fi

echo "✅ Credentials обновлены успешно!"
echo "🔍 Проверка подключения..."

# Проверяем подключение
if docker exec -e PGPASSWORD=$POSTGRES_PASSWORD devops_mock_db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Подключение к БД работает!"
else
    echo "❌ Подключение не работает. Проверьте логи: docker compose logs db"
    exit 1
fi

