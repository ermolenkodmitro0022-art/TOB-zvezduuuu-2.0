"""
Калькулятор Stars <-> UAH.
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.queries import get_user, get_all_settings
from locales.texts import t
from keyboards.client_kb import calc_direction_keyboard, back_to_menu_keyboard
from states.fsm import CalculatorFSM
# Подключаем новые функции умного расчёта интерполяции
from utils.helpers import calculate_price_interpolated, calculate_stars_from_uah_interpolated, get_mode_display

router = Router()
logger = logging.getLogger(__name__)


async def _get_lang(user_id: int) -> str:
    user = await get_user(user_id)
    return user["language"] if user and user["language"] else "ua"


@router.callback_query(F.data.startswith("calc:"), CalculatorFSM.choose_direction)
async def callback_calc_direction(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор направления конвертации."""
    try:
        lang = await _get_lang(callback.from_user.id)
        direction = callback.data.split(":")[1]

        if direction == "stars_to_uah":
            await callback.message.edit_text(
                t("calc_enter_stars", lang),
                parse_mode="HTML",
            )
            await state.update_data(
                direction="stars_to_uah",
                last_bot_msg=callback.message.message_id,
            )
        else:
            await callback.message.edit_text(
                t("calc_enter_uah", lang),
                parse_mode="HTML",
            )
            await state.update_data(
                direction="uah_to_stars",
                last_bot_msg=callback.message.message_id,
            )

        await state.set_state(CalculatorFSM.enter_amount)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_calc_direction: {e}", exc_info=True)
        await callback.answer(t("error_generic", "ua"), show_alert=True)


@router.message(CalculatorFSM.enter_amount)
async def process_calc_amount(message: Message, state: FSMContext) -> None:
    """Обработка ввода суммы для калькулятора."""
    try:
        lang = await _get_lang(message.from_user.id)
        data = await state.get_data()
        direction = data.get("direction")
        prev_bot_msg_id = data.get("last_bot_msg")

        # Удаляем предыдущее сообщение бота и ввод юзера для чистоты интерфейса
        if prev_bot_msg_id:
            try:
                await message.bot.delete_message(message.chat.id, prev_bot_msg_id)
            except Exception:
                pass
        try:
            await message.delete()
        except Exception:
            pass

        try:
            amount_str = message.text.strip().replace(",", ".") if message.text else ""
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            msg = await message.answer(
                t("calc_invalid", lang),
                parse_mode="HTML",
            )
            await state.update_data(last_bot_msg=msg.message_id)
            return

        settings = await get_all_settings()
        mode = settings.get("active_mode", "standard")
        mode_display = get_mode_display(mode, lang)

        # Применяем новые функции интерполяции вместо старых жестких тарифов
        if direction == "stars_to_uah":
            stars = int(amount)
            price = calculate_price_interpolated(stars, settings, mode)
            result_text = t("calc_result_stars_to_uah", lang,
                            stars=stars,
                            price=str(price))
        else:
            uah = amount
            stars = calculate_stars_from_uah_interpolated(uah, settings, mode)
            result_text = t("calc_result_uah_to_stars", lang,
                            uah=f"{uah:.0f}" if uah.is_integer() else f"{uah:.2f}",
                            stars=stars)

        msg = await message.answer(
            result_text,
            reply_markup=back_to_menu_keyboard(lang),
            parse_mode="HTML",
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_calc_amount: {e}", exc_info=True)
        await message.answer(t("error_generic", lang), parse_mode="HTML")