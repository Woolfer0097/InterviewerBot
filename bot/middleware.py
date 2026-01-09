from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from bot.config import Config
from bot.logging import logger


class WhitelistMiddleware(BaseMiddleware):
    """Middleware для проверки whitelist пользователей."""
    
    def __init__(self, whitelist: set[int]):
        self.whitelist = whitelist
        self.enabled = len(whitelist) > 0
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Если whitelist не настроен, пропускаем всех
        if not self.enabled:
            return await handler(event, data)
        
        # Получаем user_id из события
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        if user_id is None:
            # Если не удалось получить user_id, пропускаем (на всякий случай)
            return await handler(event, data)
        
        # Проверяем whitelist
        if user_id not in self.whitelist:
            logger.warning(f"Access denied for user {user_id} (not in whitelist)")
            
            # Отправляем сообщение об отказе в доступе
            if isinstance(event, Message):
                await event.answer(
                    "Доступ запрещен.\n\n"
                    "Обратитесь к администратору @Woolfer0097 чтобы он добавил вас в белый список.\n\n"
                    f"Ваш ID: `{user_id}`",
                    parse_mode="Markdown"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    f"Доступ запрещен\n\nОбратитесь к @Woolfer0097\nВаш ID: {user_id}",
                    show_alert=True
                )
            
            return  # Прерываем выполнение handler
        
        # Пользователь в whitelist, продолжаем
        return await handler(event, data)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для предоставления сессии БД, bot и config в handlers."""
    
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        bot: Bot,
        config: Config,
    ):
        self.sessionmaker = sessionmaker
        self.bot = bot
        self.config = config
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.sessionmaker() as session:
            data["session"] = session
            data["bot"] = self.bot
            data["config"] = self.config
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

