"""
Обработка кнопок главного меню (reply-клавиатура).
Перенаправляет в соответствующие хэндлеры.
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.queries import get_user, get_all_settings
from locales.texts import t, TEXTS
from keyboards.client_kb import (
    main_menu_keyboard,
    star_packages_keyboard,
    calc_direction_keyboard,
)
from states.fsm import PurchaseFSM, CalculatorFSM

router = Router()
logger = logging.getLogger(__name__)


async def _get_lang(user_id: int) -> str:
    """Получает язык пользователя из БД."""
    user = await get_user(user_id)
    return user["language"] if user and user["language"] else "ua"


@router.message(F.text.in_([
    TEXTS["btn_buy"]["ua"], TEXTS["btn_buy"]["ru"],
]))
async def menu_buy_stars(message: Message, state: FSMContext) -> None:
    """Кнопка «Купить Stars» — показ пакетов."""
    try:
        await state.clear()
        lang = await _get_lang(message.from_user.id)

        # Проверяем активный заказ
        from database.queries import get_active_order
        active = await get_active_order(message.from_user.id)
        if active:
            await message.answer(
                t("has_active_order", lang, order_id=active["id"]),
                parse_mode="HTML",
            )
            return

        settings = await get_all_settings()
        mode = settings.get("active_mode", "standard")

        msg = await message.answer(
            t("choose_package", lang),
            reply_markup=star_packages_keyboard(lang, settings, mode),
            parse_mode="HTML",
        )

        await state.set_state(PurchaseFSM.choose_package)
        await state.update_data(last_bot_msg=msg.message_id)
    except Exception as e:
        logger.error(f"Error in menu_buy_stars: {e}", exc_info=True)


@router.message(F.text.in_([
    TEXTS["btn_calc"]["ua"], TEXTS["btn_calc"]["ru"],
]))
async def menu_calculator(message: Message, state: FSMContext) -> None:
    """Кнопка «Калькулятор»."""
    try:
        await state.clear()
        lang = await _get_lang(message.from_user.id)
        msg = await message.answer(
            t("calc_choose_direction", lang),
            reply_markup=calc_direction_keyboard(lang),
            parse_mode="HTML",
        )
        await state.set_state(CalculatorFSM.choose_direction)
        await state.update_data(last_bot_msg=msg.message_id)
    except Exception as e:
        logger.error(f"Error in menu_calculator: {e}", exc_info=True)


@router.message(F.text.in_([
    TEXTS["btn_orders"]["ua"], TEXTS["btn_orders"]["ru"],
]))
async def menu_my_orders(message: Message, state: FSMContext) -> None:
    """Кнопка «Мои заказы»."""
    try:
        await state.clear()
        lang = await _get_lang(message.from_user.id)

        from database.queries import get_user_orders
        from utils.helpers import get_status_emoji

        orders = await get_user_orders(message.from_user.id)
        if not orders:
            await message.answer(t("no_orders", lang), parse_mode="HTML")
            return

        text = t("orders_header", lang)
        for order in orders:
            status_key = f"status_{order['status']}"
            status_text = t(status_key, lang)
            status_emoji = get_status_emoji(order["status"])
            date = order["created_at"][:16] if order["created_at"] else ""
            text += t("order_line", lang,
                      status_emoji=status_emoji,
                      id=order["id"],
                      stars=order["stars_amount"],
                      price=order["price_uah"],
                      status_text=status_text,
                      date=date)

        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in menu_my_orders: {e}", exc_info=True)


@router.message(F.text.in_([
    TEXTS["btn_reviews"]["ua"], TEXTS["btn_reviews"]["ru"],
]))
async def menu_reviews(message: Message, state: FSMContext) -> None:
    """Кнопка «Отзывы» — показ последних отзывов."""
    try:
        await state.clear()
        lang = await _get_lang(message.from_user.id)

        from database.queries import get_reviews

        reviews = await get_reviews(limit=10)
        if not reviews:
            await message.answer(t("no_reviews", lang), parse_mode="HTML")
            return

        text = t("reviews_header", lang)
        for rev in reviews:
            user_display = f"@{rev['username']}" if rev['username'] else rev['first_name']
            text += f"\n\n💬 <b>{user_display}</b>:\n<i>{rev['text']}</i>"

        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in menu_reviews: {e}", exc_info=True)


@router.message(F.text.in_([
    TEXTS["btn_info"]["ua"], TEXTS["btn_info"]["ru"],
]))
async def menu_info(message: Message, state: FSMContext) -> None:
    """Кнопка «Инструкция»."""
    try:
        await state.clear()
        lang = await _get_lang(message.from_user.id)
        await message.answer(t("info_text", lang), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in menu_info: {e}", exc_info=True)


# ──────────────── Общие callback-и ────────────────

@router.callback_query(F.data == "back:menu")
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в главное меню по inline-кнопке."""
    try:
        await state.clear()
        lang = await _get_lang(callback.from_user.id)

        # Удаляем inline-сообщение
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            t("back_to_menu", lang),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_back_to_menu: {e}", exc_info=True)


@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery) -> None:
    """Заглушка для информационных кнопок."""
    await callback.answer()