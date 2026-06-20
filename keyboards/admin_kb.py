"""
Клавиатуры для админ-панели.
"""

from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_panel_keyboard(active_mode: str) -> InlineKeyboardMarkup:
    """Панель администратора — настройки цен и режим."""
    mode_emoji = "🔥" if active_mode == "dump" else "🚀"
    mode_text = "ДЕМПІНГ" if active_mode == "dump" else "СТАНДАРТ"
    toggle_to = "standard" if active_mode == "dump" else "dump"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⚙️ Налаштування цін пакетів",
                callback_data="admin:package_prices_menu",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"{mode_emoji} Режим: {mode_text} ↔️",
                callback_data=f"admin:toggle_mode:{toggle_to}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 Оновити",
                callback_data="admin:refresh",
            ),
        ],
    ])

def admin_package_prices_keyboard(mode: str) -> InlineKeyboardMarkup:
    """Клавиатура управления фиксированными ценами пакетов."""
    mode_prefix = "🚀 Стандарт" if mode == "standard" else "🔥 Демпінг"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📦 {mode_prefix}: Изменить 50 Stars", callback_data=f"admin:edit_pkg:50:{mode}")],
        [InlineKeyboardButton(text=f"📦 {mode_prefix}: Изменить 100 Stars", callback_data=f"admin:edit_pkg:100:{mode}")],
        [InlineKeyboardButton(text=f"📦 {mode_prefix}: Изменить 250 Stars", callback_data=f"admin:edit_pkg:250:{mode}")],
        [InlineKeyboardButton(text=f"📦 {mode_prefix}: Изменить 500 Stars", callback_data=f"admin:edit_pkg:500:{mode}")],
        [InlineKeyboardButton(text=f"📦 {mode_prefix}: Изменить 1000 Stars", callback_data=f"admin:edit_pkg:1000:{mode}")],
        [InlineKeyboardButton(text=f"⬅️ Назад", callback_data="admin:refresh")]
    ])


def admin_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Кнопки управления заказом для админа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⏳ Оплата отримана",
                callback_data=f"aord:paid:{order_id}",
            ),
            InlineKeyboardButton(
                text="✅ Замовлення доставлено",
                callback_data=f"aord:delivered:{order_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="⏱ Затримка",
                callback_data=f"aord:delay:{order_id}",
            ),
            InlineKeyboardButton(
                text="❌ Скасувати",
                callback_data=f"aord:cancel:{order_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="✉️ Написати клієнту",
                callback_data=f"aord:message:{order_id}",
            ),
            InlineKeyboardButton(
                text="🚫 Забанити",
                callback_data=f"aord:ban:{order_id}",
            ),
        ],
    ])


def admin_order_closed_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Клавиатура для закрытого заказа (только информация)."""
    status_map = {
        "delivered": "✅ Доставлено",
        "cancelled": "❌ Скасовано",
        "processing": "🔄 В обробці",
        "paid": "💸 Оплачено",
    }
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"📋 Статус: {status_map.get(status, status)}",
                callback_data="noop",
            ),
        ],
    ])
