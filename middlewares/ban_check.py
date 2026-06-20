"""
Middleware для проверки бана пользователя.
Забаненные пользователи не могут использовать бота.
"""

from __future__ import annotations
from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from database.queries import is_banned, get_user
from config import ADMIN_ID


class BanCheckMiddleware(BaseMiddleware):
    """Проверяет, заблокирован ли пользователь, перед каждым апдейтом."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Определяем user_id из разных типов событий
        user_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        # Пропускаем админа и неопознанных
        if user_id is None or user_id == ADMIN_ID:
            return await handler(event, data)

        # Проверяем бан
        if await is_banned(user_id):
            if isinstance(event, Message):
                from locales.texts import t
                user = await get_user(user_id)
                lang = user.get("language", "ua") if user else "ua"
                await event.answer(t("banned", lang))
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫", show_alert=True)
            return  # Не передаём дальше

        return await handler(event, data)
