# Docker Init Scripts

Эти скрипты выполняются только при первой инициализации БД.

Для решения проблемы с аутентификацией после обновлений:

1. **Убедитесь, что credentials в docker-compose.yml совпадают с DATABASE_URL в .env**
2. **Используйте фиксированные credentials** - не меняйте POSTGRES_USER и POSTGRES_PASSWORD
3. **Если проблема сохраняется**, выполните:

```bash
# Остановить контейнеры
docker compose down

# Подключиться к volume и исправить пароль вручную (если нужно)
docker run --rm -v interviewbot_postgres_data:/data -it postgres:16-alpine sh

# Или просто пересоздать volume (удалит данные!)
docker volume rm interviewbot_postgres_data
docker compose up -d
```

**Рекомендация**: Всегда используйте одинаковые credentials в docker-compose.yml и .env файле.

