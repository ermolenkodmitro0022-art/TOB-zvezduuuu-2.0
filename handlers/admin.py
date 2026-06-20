"""
Админ-панель: настройки ценообразования и управление заказами.
Все действия доступны ТОЛЬКО для ADMIN_ID.
"""

from __future__ import annotations
import asyncio
import logging

from aiogram import Router, F, Bot
# pyrefly: ignore [missing-import]
from aiogram.types import Message, CallbackQuery
# pyrefly: ignore [missing-import]
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards.admin_kb import admin_panel_keyboard, admin_package_prices_keyboard

from database.queries import (
    get_user, get_all_settings, set_setting,
    get_order, update_order_status, ban_user,
    count_completed_orders, update_order_admin_message,
)
from locales.texts import t
from keyboards.admin_kb import (
    admin_panel_keyboard,
    admin_order_keyboard,
    admin_order_closed_keyboard,
)
from keyboards.client_kb import review_keyboard, main_menu_keyboard
from states.fsm import AdminSettingsFSM, AdminOrderFSM
from utils.helpers import get_mode_display
from config import ADMIN_ID

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ──────────────── /admin — Панель ────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    """Команда /admin — показывает панель настроек."""
    if not _is_admin(message.from_user.id):
        user = await get_user(message.from_user.id)
        lang = user["language"] if user and user["language"] else "ua"
        await message.answer(t("not_admin", lang), parse_mode="HTML")
        return

    await state.clear()
    await _show_admin_panel(message, state)


async def _show_admin_panel(
    target: Message | CallbackQuery,
    state: FSMContext,
    edit: bool = False,
) -> None:
    """Формирует и отправляет/редактирует панель админа."""
    settings = await get_all_settings()
    total = await count_completed_orders()
    mode = settings.get("active_mode", "standard")
    mode_display = get_mode_display(mode, "ua")

    text = t("admin_panel", "ua",
             price_100_dump=settings.get("price_100_dump", "73.0"),
             price_100_standard=settings.get("price_100_standard", "80.0"),
             active_mode=mode_display,
             total_orders=total)

    kb = admin_panel_keyboard(mode)

    if edit and isinstance(target, CallbackQuery):
        from aiogram.exceptions import TelegramBadRequest
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
    elif isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


# ──────────────── НАСТРОЙКИ ЦЕНЫ ────────────────

@router.callback_query(F.data == "admin:set_price_100_dump")
async def admin_set_price_100_dump(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return
    await callback.message.edit_text(
        t("admin_enter_price_100_dump", "ua"), parse_mode="HTML"
    )
    await state.set_state(AdminSettingsFSM.enter_price_100_dump)
    await state.update_data(admin_msg_id=callback.message.message_id)
    await callback.answer()


@router.callback_query(F.data == "admin:set_price_100_standard")
async def admin_set_price_100_standard(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return
    await callback.message.edit_text(
        t("admin_enter_price_100_standard", "ua"), parse_mode="HTML"
    )
    await state.set_state(AdminSettingsFSM.enter_price_100_standard)
    await state.update_data(admin_msg_id=callback.message.message_id)
    await callback.answer()


@router.message(AdminSettingsFSM.enter_price_100_dump)
async def process_price_100_dump(message: Message, state: FSMContext) -> None:
    await _process_setting(message, state, "price_100_dump")


@router.message(AdminSettingsFSM.enter_price_100_standard)
async def process_price_100_standard(message: Message, state: FSMContext) -> None:
    await _process_setting(message, state, "price_100_standard")


async def _process_setting(message: Message, state: FSMContext, key: str) -> None:
    """Универсальный обработчик ввода числовой настройки."""
    if not _is_admin(message.from_user.id):
        return

    try:
        text = message.text.strip().replace(",", ".") if message.text else ""
        value = float(text)
        if value < 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer(t("admin_invalid_number", "ua"), parse_mode="HTML")
        return

    await set_setting(key, str(value))

    # Удаляем промежуточные
    data = await state.get_data()
    prev_id = data.get("admin_msg_id")
    if prev_id:
        try:
            await message.bot.delete_message(message.chat.id, prev_id)
        except Exception:
            pass
    try:
        await message.delete()
    except Exception:
        pass

    await state.clear()
    await message.answer(t("admin_setting_saved", "ua"), parse_mode="HTML")
    await _show_admin_panel(message, state)


# ──────────────── ПЕРЕКЛЮЧАТЕЛЬ РЕЖИМА ────────────────

@router.callback_query(F.data.startswith("admin:toggle_mode:"))
async def admin_toggle_mode(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return

    new_mode = callback.data.split(":")[2]  # "dump" или "standard"
    await set_setting("active_mode", new_mode)

    mode_display = get_mode_display(new_mode, "ua")
    await callback.answer(f"✅ Режим: {mode_display}", show_alert=True)

    await _show_admin_panel(callback, state, edit=True)


@router.callback_query(F.data == "admin:refresh")
async def admin_refresh(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return
    await _show_admin_panel(callback, state, edit=True)
    await callback.answer("🔄")

# ──────────────── УПРАВЛЕНИЕ ЦЕНАМИ ПАКЕТОВ ────────────────

@router.callback_query(F.data == "admin:package_prices_menu")
async def admin_package_prices_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return
    
    settings = await get_all_settings()
    mode = settings.get("active_mode", "standard")
    
    p50 = settings.get(f"price_50_{mode}", "40.0")
    p100 = settings.get(f"price_100_{mode}", "80.0")
    p250 = settings.get(f"price_250_{mode}", "200.0")
    p500 = settings.get(f"price_500_{mode}", "400.0")
    p1000 = settings.get(f"price_1000_{mode}", "800.0")
    
    mode_text = "🚀 СТАНДАРТ" if mode == "standard" else "🔥 ДЕМПІНГ"
    
    text = (
        f"<b>⚙️ Налаштування цін пакетів ({mode_text})</b>\n\n"
        f"Поточні фіксовані ціни:\n"
        f"• 50 Stars — <code>{p50}</code> UAH\n"
        f"• 100 Stars — <code>{p100}</code> UAH\n"
        f"• 250 Stars — <code>{p250}</code> UAH\n"
        f"• 500 Stars — <code>{p500}</code> UAH\n"
        f"• 1000 Stars — <code>{p1000}</code> UAH\n\n"
        f"<i>Оберіть пакет, ціну которого бажаєте змінити:</i>"
    )
    
    await callback.message.edit_text(text, reply_markup=admin_package_prices_keyboard(mode), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:edit_pkg:"))
async def admin_edit_package_price(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return
        
    parts = callback.data.split(":")
    pkg_volume = parts[2]
    mode = parts[3]
    
    await state.set_state(AdminSettingsFSM.enter_package_price)
    await state.update_data(edit_pkg_key=f"price_{pkg_volume}_{mode}", admin_msg_id=callback.message.message_id)
    
    await callback.message.edit_text(
        f"📥 <b>Введіть нову ціну у гривнях для пакета {pkg_volume} Stars ({mode}):</b>", 
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminSettingsFSM.enter_package_price)
async def process_custom_package_price(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return

    try:
        text = message.text.strip().replace(",", ".") if message.text else ""
        value = float(text)
        if value < 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("❌ Будь ласка, введіть коректне число більше 0.", parse_mode="HTML")
        return

    data = await state.get_data()
    setting_key = data.get("edit_pkg_key")
    
    if setting_key:
        await set_setting(setting_key, str(value))

    prev_id = data.get("admin_msg_id")
    if prev_id:
        try:
            await message.bot.delete_message(message.chat.id, prev_id)
        except Exception:
            pass
    try:
        await message.delete()
    except Exception:
        pass

    await state.clear()
    
    settings = await get_all_settings()
    mode = settings.get("active_mode", "standard")
    p50 = settings.get(f"price_50_{mode}", "40.0")
    p100 = settings.get(f"price_100_{mode}", "80.0")
    p250 = settings.get(f"price_250_{mode}", "200.0")
    p500 = settings.get(f"price_500_{mode}", "400.0")
    p1000 = settings.get(f"price_1000_{mode}", "800.0")
    mode_text = "🚀 СТАНДАРТ" if mode == "standard" else "🔥 ДЕМПІНГ"
    
    text = (
        f"✅ <b>Налаштування успішно збережено!</b>\n\n"
        f"<b>⚙️ Налаштування цін пакетів ({mode_text})</b>\n\n"
        f"Поточні фіксовані ціни:\n"
        f"• 50 Stars — <code>{p50}</code> UAH\n"
        f"• 100 Stars — <code>{p100}</code> UAH\n"
        f"• 250 Stars — <code>{p250}</code> UAH\n"
        f"• 500 Stars — <code>{p500}</code> UAH\n"
        f"• 1000 Stars — <code>{p1000}</code> UAH\n"
    )
    await message.answer(text, reply_markup=admin_package_prices_keyboard(mode), parse_mode="HTML")

# ════════════════════════════════════════════════════
#          УПРАВЛЕНИЕ ЗАКАЗАМИ (6 действий)
# ════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("aord:paid:"))
async def admin_order_paid(callback: CallbackQuery, state: FSMContext) -> None:
    """Админ подтверждает получение оплаты."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return

    try:
        order_id = int(callback.data.split(":")[2])
        order = await get_order(order_id)
        if not order:
            await callback.answer("❌ Замовлення не знайдено", show_alert=True)
            return

        await update_order_status(order_id, "processing")

        # Уведомляем клиента
        user = await get_user(order["user_id"])
        lang = user["language"] if user and user["language"] else "ua"

        await callback.bot.send_message(
            chat_id=order["user_id"],
            text=t("order_accepted", lang, order_id=order_id),
            parse_mode="HTML",
        )

        # Обновляем кнопки у админа (оставляем управление)
        await callback.message.edit_reply_markup(
            reply_markup=admin_order_keyboard(order_id),
        )
        await callback.answer(
            t("admin_order_status_updated", "ua", order_id=order_id, status="🔄 В обробці"),
            show_alert=True,
        )
    except Exception as e:
        logger.error(f"Error in admin_order_paid: {e}", exc_info=True)
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(F.data.startswith("aord:delivered:"))
async def admin_order_delivered(callback: CallbackQuery, state: FSMContext) -> None:
    """Админ подтверждает доставку Stars."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return

    try:
        order_id = int(callback.data.split(":")[2])
        order = await get_order(order_id)
        if not order:
            await callback.answer("❌ Замовлення не знайдено", show_alert=True)
            return

        await update_order_status(order_id, "delivered")

        # Уведомляем клиента
        user = await get_user(order["user_id"])
        lang = user["language"] if user and user["language"] else "ua"

        await callback.bot.send_message(
            chat_id=order["user_id"],
            text=t("order_delivered", lang,
                    order_id=order_id,
                    stars=order["stars_amount"],
                    recipient=order["recipient_username"]),
            parse_mode="HTML",
        )

        # Закрываем кнопки у админа
        await callback.message.edit_reply_markup(
            reply_markup=admin_order_closed_keyboard(order_id, "delivered"),
        )
        await callback.answer("✅ Замовлення закрито!", show_alert=True)

        # Через 5 секунд предлагаем клиенту оставить отзыв
        asyncio.create_task(
            _send_review_prompt(callback.bot, order["user_id"], order_id, lang)
        )
    except Exception as e:
        logger.error(f"Error in admin_order_delivered: {e}", exc_info=True)
        await callback.answer("❌ Помилка", show_alert=True)


async def _send_review_prompt(bot: Bot, user_id: int, order_id: int, lang: str) -> None:
    """Отправляет предложение оставить отзыв через 5 секунд."""
    try:
        await asyncio.sleep(5)
        await bot.send_message(
            chat_id=user_id,
            text=t("leave_review", lang),
            reply_markup=review_keyboard(lang, order_id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Error sending review prompt: {e}", exc_info=True)


@router.callback_query(F.data.startswith("aord:delay:"))
async def admin_order_delay(callback: CallbackQuery, state: FSMContext) -> None:
    """Админ вводит время задержки."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return

    order_id = int(callback.data.split(":")[2])
    await state.set_state(AdminOrderFSM.enter_delay_time)
    await state.update_data(admin_action_order_id=order_id)

    await callback.message.answer(
        t("admin_enter_delay", "ua"), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminOrderFSM.enter_delay_time)
async def process_delay_time(message: Message, state: FSMContext) -> None:
    """Обработка ввода времени задержки."""
    if not _is_admin(message.from_user.id):
        return

    try:
        data = await state.get_data()
        order_id = data.get("admin_action_order_id")
        delay_time = message.text.strip() if message.text else "невідомо"

        order = await get_order(order_id)
        if not order:
            await message.answer("❌ Замовлення не знайдено")
            await state.clear()
            return

        user = await get_user(order["user_id"])
        lang = user["language"] if user and user["language"] else "ua"

        await message.bot.send_message(
            chat_id=order["user_id"],
            text=t("order_delayed", lang,
                    order_id=order_id, delay_time=delay_time),
            parse_mode="HTML",
        )

        await message.answer("✅ Клієнта повідомлено про затримку.")
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_delay_time: {e}", exc_info=True)
        await state.clear()


@router.callback_query(F.data.startswith("aord:cancel:"))
async def admin_order_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Админ отменяет заказ — просит причину."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return

    order_id = int(callback.data.split(":")[2])
    await state.set_state(AdminOrderFSM.enter_cancel_reason)
    await state.update_data(admin_action_order_id=order_id)

    await callback.message.answer(
        t("admin_enter_cancel_reason", "ua"), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminOrderFSM.enter_cancel_reason)
async def process_cancel_reason(message: Message, state: FSMContext) -> None:
    """Обработка причины отмены."""
    if not _is_admin(message.from_user.id):
        return

    try:
        data = await state.get_data()
        order_id = data.get("admin_action_order_id")
        reason = message.text.strip() if message.text else "Не вказано"

        order = await get_order(order_id)
        if not order:
            await message.answer("❌ Замовлення не знайдено")
            await state.clear()
            return

        await update_order_status(order_id, "cancelled", reason)

        user = await get_user(order["user_id"])
        lang = user["language"] if user and user["language"] else "ua"

        await message.bot.send_message(
            chat_id=order["user_id"],
            text=t("order_cancelled_by_admin", lang,
                    order_id=order_id, reason=reason),
            parse_mode="HTML",
        )

        # Закрываем кнопки
        if order.get("admin_message_id"):
            try:
                await message.bot.edit_message_reply_markup(
                    chat_id=ADMIN_ID,
                    message_id=order["admin_message_id"],
                    reply_markup=admin_order_closed_keyboard(order_id, "cancelled"),
                )
            except Exception:
                pass

        await message.answer("✅ Замовлення скасовано, клієнта повідомлено.")
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_cancel_reason: {e}", exc_info=True)
        await state.clear()


@router.callback_query(F.data.startswith("aord:message:"))
async def admin_order_message(callback: CallbackQuery, state: FSMContext) -> None:
    """Админ хочет написать клиенту."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return

    order_id = int(callback.data.split(":")[2])
    await state.set_state(AdminOrderFSM.enter_message)
    await state.update_data(admin_action_order_id=order_id)

    await callback.message.answer(
        t("admin_enter_message", "ua"), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminOrderFSM.enter_message)
async def process_admin_message(message: Message, state: FSMContext) -> None:
    """Отправка сообщения админа клиенту."""
    if not _is_admin(message.from_user.id):
        return

    try:
        data = await state.get_data()
        order_id = data.get("admin_action_order_id")
        text = message.text.strip() if message.text else ""

        order = await get_order(order_id)
        if not order:
            await message.answer("❌ Замовлення не знайдено")
            await state.clear()
            return

        user = await get_user(order["user_id"])
        lang = user["language"] if user and user["language"] else "ua"

        await message.bot.send_message(
            chat_id=order["user_id"],
            text=t("admin_message_to_client", lang,
                    order_id=order_id, message=text),
            parse_mode="HTML",
        )

        await message.answer(t("admin_message_sent", "ua"), parse_mode="HTML")
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_admin_message: {e}", exc_info=True)
        await state.clear()


@router.callback_query(F.data.startswith("aord:ban:"))
async def admin_ban_user(callback: CallbackQuery, state: FSMContext) -> None:
    """Админ банит клиента."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("🚫", show_alert=True)
        return

    try:
        order_id = int(callback.data.split(":")[2])
        order = await get_order(order_id)
        if not order:
            await callback.answer("❌ Замовлення не знайдено", show_alert=True)
            return

        await ban_user(order["user_id"])
        await callback.answer(
            t("admin_user_banned", "ua"), show_alert=True
        )
    except Exception as e:
        logger.error(f"Error in admin_ban_user: {e}", exc_info=True)
        await callback.answer("❌ Помилка", show_alert=True)
