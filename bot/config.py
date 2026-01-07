import os
from dataclasses import dataclass
from typing import Set
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    database_url: str
    tz: str
    daily_hour: int
    daily_minute: int
    questions_per_day: int
    high_score_threshold: int
    whitelist: Set[int]

    @classmethod
    def from_env(cls) -> "Config":
        # Парсим whitelist из env (формат: "123456789,987654321" или пустая строка для отключения)
        whitelist_str = os.getenv("WHITELIST_TG_IDS", "").strip()
        whitelist: Set[int] = set()
        if whitelist_str:
            try:
                whitelist = {int(uid.strip()) for uid in whitelist_str.split(",") if uid.strip()}
            except ValueError:
                # Если есть невалидные значения, игнорируем их
                pass
        
        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            database_url=os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/devops_mock"),
            tz=os.getenv("TZ", "Europe/Moscow"),
            daily_hour=int(os.getenv("DAILY_HOUR", "9")),
            daily_minute=int(os.getenv("DAILY_MINUTE", "0")),
            questions_per_day=int(os.getenv("QUESTIONS_PER_DAY", "5")),
            high_score_threshold=int(os.getenv("HIGH_SCORE_THRESHOLD", "5")),
            whitelist=whitelist,
        )

