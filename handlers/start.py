"""
Хэндлер /start — выбор языка и приветствие.
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from database.queries import get_user, create_user, update_language, update_username
from locales.texts import t
from keyboards.client_kb import language_keyboard, main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработка команды /start."""
    try:
        await state.clear()  # Сброс любого FSM-состояния

        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""

        user = await get_user(user_id)

        if user is None:
            # Новый пользователь — создаём и просим выбрать язык
            await create_user(user_id, username, first_name)
            await message.answer(
                t("choose_language", "ua"),
                reply_markup=language_keyboard(),
                parse_mode="HTML",
            )
        elif not user["language"]:
            # Пользователь есть, но язык не выбран
            await message.answer(
                t("choose_language", "ua"),
                reply_markup=language_keyboard(),
                parse_mode="HTML",
            )
        else:
            # Возвращающийся пользователь — обновляем данные и показываем меню
            await update_username(user_id, username, first_name)
            lang = user["language"]
            await message.answer(
                t("welcome", lang),
                reply_markup=main_menu_keyboard(lang),
                parse_mode="HTML",
            )
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}", exc_info=True)
        await message.answer("❌ Error. Please try /start again.")


@router.callback_query(F.data.startswith("lang:"))
async def callback_language(callback: CallbackQuery) -> None:
    """Обработка выбора языка."""
    try:
        lang = callback.data.split(":")[1]  # "ua" или "ru"
        user_id = callback.from_user.id
        username = callback.from_user.username or ""
        first_name = callback.from_user.first_name or ""

        await update_language(user_id, lang)
        await update_username(user_id, username, first_name)

        # Удаляем кнопки выбора языка
        await callback.message.edit_text(
            t("lang_set", lang),
            parse_mode="HTML",
        )

        # Отправляем приветствие с главным меню
        await callback.message.answer(
            t("welcome", lang),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_language: {e}", exc_info=True)
        await callback.answer("❌ Error", show_alert=True)
