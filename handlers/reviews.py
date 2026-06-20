"""
Обработчик отзывов.
После доставки заказа — предложение оставить отзыв.
Текст отзыва отправляется в канал.
"""

from __future__ import annotations
import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.queries import get_user, get_order, save_review
from locales.texts import t
from keyboards.client_kb import main_menu_keyboard
from states.fsm import ReviewFSM
from config import CHANNEL_ID

router = Router()
logger = logging.getLogger(__name__)


async def _get_lang(user_id: int) -> str:
    user = await get_user(user_id)
    return user["language"] if user and user["language"] else "ua"


@router.callback_query(F.data.startswith("review:"))
async def callback_review(callback: CallbackQuery, state: FSMContext) -> None:
    """Клиент нажал «Оставить отзыв» или «Пропустить»."""
    try:
        lang = await _get_lang(callback.from_user.id)
        value = callback.data.split(":")[1]

        if value == "skip":
            await callback.message.edit_text(
                t("review_skipped", lang),
                parse_mode="HTML",
            )
            await state.clear()
            await callback.answer()
            return

        # value — это order_id
        order_id = int(value)
        await state.update_data(review_order_id=order_id)
        await state.set_state(ReviewFSM.enter_text)

        await callback.message.edit_text(
            t("enter_review_text", lang),
            parse_mode="HTML",
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_review: {e}", exc_info=True)
        await callback.answer("❌", show_alert=True)


@router.message(ReviewFSM.enter_text)
async def process_review_text(message: Message, state: FSMContext) -> None:
    """Обработка текста отзыва — сохранение в БД и отправка в канал."""
    try:
        lang = await _get_lang(message.from_user.id)
        data = await state.get_data()
        order_id = data.get("review_order_id")

        if not order_id or not message.text:
            await message.answer(t("error_generic", lang), parse_mode="HTML")
            await state.clear()
            return

        review_text = message.text.strip()[:1000]  # Ограничение длины

        # Сохраняем в БД
        await save_review(order_id, message.from_user.id, review_text)

        # Получаем данные заказа
        order = await get_order(order_id)
        user = await get_user(message.from_user.id)

        user_display = f"@{user['username']}" if user.get("username") else user.get("first_name", "Клієнт")

        # Отправляем в канал
        if CHANNEL_ID:
            channel_text = t("review_channel_format", lang,
                             user=user_display,
                             text=review_text,
                             stars=order["stars_amount"] if order else "?")
            try:
                await message.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=channel_text,
                    parse_mode="HTML",
                )
            except Exception as ce:
                logger.error(f"Failed to send review to channel: {ce}")

        await message.answer(
            t("review_saved", lang),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_review_text: {e}", exc_info=True)
        await state.clear()
