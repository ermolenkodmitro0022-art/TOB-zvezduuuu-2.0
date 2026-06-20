"""
Клавиатуры для клиентского интерфейса.
"""

from __future__ import annotations
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from locales.texts import t
from config import STAR_PACKAGES


def language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang:ua"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        ]
    ])


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Главное меню (reply-клавиатура)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_buy", lang))],
            [
                KeyboardButton(text=t("btn_calc", lang)),
                KeyboardButton(text=t("btn_orders", lang)),
            ],
            [
                KeyboardButton(text=t("btn_reviews", lang)),
                KeyboardButton(text=t("btn_info", lang)),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def star_packages_keyboard(lang: str, settings: dict, mode: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора пакета Stars с ценами."""
    from utils.helpers import calculate_price_interpolated

    buttons = []
    for stars in STAR_PACKAGES:
        price = calculate_price_interpolated(stars, settings, mode)
        buttons.append([
            InlineKeyboardButton(
                text=f"⭐️ {stars} Stars — {price} ₴",
                callback_data=f"pkg:{stars}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text=t("btn_custom_amount", lang),
            callback_data="pkg:custom",
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            text=t("btn_back", lang),
            callback_data="back:menu",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def recipient_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Кнопки «Себе» / «Другу»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("btn_for_self", lang),
                callback_data="recipient:self",
            ),
            InlineKeyboardButton(
                text=t("btn_for_friend", lang),
                callback_data="recipient:friend",
            ),
        ],
        [
            InlineKeyboardButton(
                text=t("btn_back", lang),
                callback_data="back:packages",
            )
        ],
    ])


def payment_keyboard(lang: str, order_id: int) -> InlineKeyboardMarkup:
    """Кнопки «Я оплатил» / «Отменить»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("btn_paid", lang),
                callback_data=f"paid:{order_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=t("btn_cancel_order", lang),
                callback_data=f"cancel_order:{order_id}",
            ),
        ],
    ])


def calc_direction_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Выбор направления конвертации в калькуляторе."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("btn_stars_to_uah", lang),
                callback_data="calc:stars_to_uah",
            ),
        ],
        [
            InlineKeyboardButton(
                text=t("btn_uah_to_stars", lang),
                callback_data="calc:uah_to_stars",
            ),
        ],
        [
            InlineKeyboardButton(
                text=t("btn_back", lang),
                callback_data="back:menu",
            ),
        ],
    ])


def review_keyboard(lang: str, order_id: int) -> InlineKeyboardMarkup:
    """Кнопки после доставки: оставить отзыв / пропустить."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("btn_leave_review", lang),
                callback_data=f"review:{order_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=t("btn_skip_review", lang),
                callback_data="review:skip",
            ),
        ],
    ])


def back_to_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Кнопка «Главное меню»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("btn_main_menu", lang),
                callback_data="back:menu",
            )
        ]
    ])