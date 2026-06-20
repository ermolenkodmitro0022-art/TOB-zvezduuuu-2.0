"""
Покупка Stars — пошаговый FSM-процесс.
Включает: выбор пакета, получателя, формирование чека,
ожидание оплаты и скриншота, уведомление админу.
"""

from __future__ import annotations
import logging
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.helpers import validate_username, calculate_price_interpolated

from database.queries import (
    get_user, get_all_settings, create_order,
    update_order_screenshot, update_order_admin_message,
    get_active_order, update_order_status,
)
from locales.texts import t
from keyboards.client_kb import (
    star_packages_keyboard, recipient_keyboard,
    payment_keyboard, main_menu_keyboard,
)
from keyboards.admin_kb import admin_order_keyboard
from states.fsm import PurchaseFSM
from utils.helpers import calculate_price_interpolated, validate_username
from config import (
    ADMIN_ID, CARD_NUMBER, CARD_HOLDER,
    MONO_JAR_LINK, MIN_STARS, MAX_STARS,
)

router = Router()
logger = logging.getLogger(__name__)


async def _get_lang(user_id: int) -> str:
    user = await get_user(user_id)
    return user["language"] if user and user["language"] else "ua"


async def _delete_prev_msg(bot: Bot, chat_id: int, state: FSMContext) -> None:
    """Удаляет предыдущее промежуточное сообщение бота (авто-очистка)."""
    data = await state.get_data()
    prev_id = data.get("last_bot_msg")
    if prev_id:
        try:
            await bot.delete_message(chat_id, prev_id)
        except Exception:
            pass


async def _get_pricing() -> tuple[float, str]:
    """Возвращает (price_100, mode)."""
    settings = await get_all_settings()
    mode = settings.get("active_mode", "standard")
    price_100 = float(settings.get(
        "price_100_dump" if mode == "dump" else "price_100_standard",
        "73.0" if mode == "dump" else "80.0"
    ))
    return price_100, mode



# ──────────────── ВЫБОР ПАКЕТА ────────────────

@router.callback_query(F.data.startswith("pkg:"), PurchaseFSM.choose_package)
async def callback_choose_package(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора пакета Stars."""
    try:
        lang = await _get_lang(callback.from_user.id)
        value = callback.data.split(":")[1]

        if value == "custom":
            # Пользователь хочет ввести своё количество
            await callback.message.edit_text(
                t("enter_custom_amount", lang, min=MIN_STARS, max=MAX_STARS),
                parse_mode="HTML",
            )
            await state.set_state(PurchaseFSM.enter_custom_amount)
            await state.update_data(last_bot_msg=callback.message.message_id)
            await callback.answer()
            return

        stars = int(value)
        settings = await get_all_settings()
        mode = settings.get("active_mode", "standard")
        price = calculate_price_interpolated(stars, settings, mode)

        await state.update_data(stars=stars, price=price)
        await state.set_state(PurchaseFSM.choose_recipient)

        await callback.message.edit_text(
            t("choose_recipient", lang),
            reply_markup=recipient_keyboard(lang),
            parse_mode="HTML",
        )
        await state.update_data(last_bot_msg=callback.message.message_id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_choose_package: {e}", exc_info=True)
        await callback.answer(t("error_generic", "ua"), show_alert=True)

@router.callback_query(F.data == "back:packages", PurchaseFSM.choose_recipient)
async def callback_back_to_packages(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к выбору пакетов."""
    try:
        lang = await _get_lang(callback.from_user.id)
        price_100, mode = await _get_pricing()

        await callback.message.edit_text(
            t("choose_package", lang),
            reply_markup=star_packages_keyboard(lang, price_100),
            parse_mode="HTML",
        )
        await state.set_state(PurchaseFSM.choose_package)
        await state.update_data(last_bot_msg=callback.message.message_id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_back_to_packages: {e}", exc_info=True)


# ──────────────── ВВОД СВОЕГО КОЛИЧЕСТВА ────────────────

@router.message(PurchaseFSM.enter_custom_amount)
async def process_custom_amount(message: Message, state: FSMContext) -> None:
    """Обработка ввода произвольного количества Stars."""
    try:
        lang = await _get_lang(message.from_user.id)
        data = await state.get_data()
        
        # Удаляем старое сообщение бота, если оно было
        prev_id = data.get("last_bot_msg")
        if prev_id:
            try: await message.bot.delete_message(message.chat.id, prev_id)
            except: pass
            
        # Удаляем сообщение пользователя
        try: await message.delete()
        except: pass

        # Парсим текст
        text = message.text.strip().replace(",", ".") if message.text else ""
        try:
            stars = int(float(text))
            if stars <= 0: raise ValueError
        except (ValueError, TypeError):
            msg = await message.answer("❌ Введіть коректне число!", parse_mode="HTML")
            await state.update_data(last_bot_msg=msg.message_id)
            return

        # Проверка: минимум 50 звезд
        if stars < 50:
            msg = await message.answer("❌ Мінімальне замовлення — 50 Stars.", parse_mode="HTML")
            await state.update_data(last_bot_msg=msg.message_id)
            return

        # Расчет цены через интерполяцию
        settings = await get_all_settings()
        mode = settings.get("active_mode", "standard")
        price = calculate_price_interpolated(stars, settings, mode)

        await state.update_data(stars=stars, price=price)
        await state.set_state(PurchaseFSM.choose_recipient)

        # Вывод клавиатуры получателя
        from keyboards.client_kb import recipient_keyboard
        msg = await message.answer(
            t("choose_recipient", lang),
            reply_markup=recipient_keyboard(lang),
            parse_mode="HTML",
        )
        await state.update_data(last_bot_msg=msg.message_id)

    except Exception as e:
        logger.error(f"Error in process_custom_amount: {e}", exc_info=True)
        await state.clear()

        stars = int(text)
        if stars < MIN_STARS or stars > MAX_STARS:
            msg = await message.answer(
                t("invalid_amount", lang, min=MIN_STARS, max=MAX_STARS),
                parse_mode="HTML",
            )
            await state.update_data(last_bot_msg=msg.message_id)
            return

        settings = await get_all_settings()
        mode = settings.get("active_mode", "standard")
        price = calculate_price_interpolated(stars, settings, mode)

        await state.update_data(stars=stars, price=price)
        await state.set_state(PurchaseFSM.choose_recipient)

        msg = await message.answer(
            t("choose_recipient", lang),
            reply_markup=recipient_keyboard(lang),
            parse_mode="HTML",
        )
        await state.update_data(last_bot_msg=msg.message_id)
    except Exception as e:
        logger.error(f"Error in process_custom_amount: {e}", exc_info=True)


# ──────────────── ВЫБОР ПОЛУЧАТЕЛЯ ────────────────

@router.callback_query(F.data.startswith("recipient:"), PurchaseFSM.choose_recipient)
async def callback_recipient(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора получателя: себе или другу."""
    try:
        lang = await _get_lang(callback.from_user.id)
        choice = callback.data.split(":")[1]

        if choice == "self":
            username = callback.from_user.username
            if not username:
                await callback.message.edit_text(
                    t("no_username", lang),
                    parse_mode="HTML",
                )
                await state.update_data(last_bot_msg=callback.message.message_id)
                await callback.answer()
                return

            recipient = f"@{username}"
            await state.update_data(recipient=recipient, for_self=True)
            await _show_receipt(callback, state, lang)
        else:
            # Другу — просим ввести username
            await callback.message.edit_text(
                t("enter_friend_username", lang),
                parse_mode="HTML",
            )
            await state.set_state(PurchaseFSM.enter_friend_username)
            await state.update_data(last_bot_msg=callback.message.message_id)

        await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_recipient: {e}", exc_info=True)
        await callback.answer(t("error_generic", "ua"), show_alert=True)


@router.message(PurchaseFSM.enter_friend_username)
async def process_friend_username(message: Message, state: FSMContext) -> None:
    """Обработка ввода username друга."""
    try:
        lang = await _get_lang(message.from_user.id)
        await _delete_prev_msg(message.bot, message.chat.id, state)

        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except Exception:
            pass

        text = message.text.strip() if message.text else ""
        validated = validate_username(text)

        if not validated:
            msg = await message.answer(
                t("invalid_username", lang),
                parse_mode="HTML",
            )
            await state.update_data(last_bot_msg=msg.message_id)
            return

        await state.update_data(recipient=validated, for_self=False)
        await state.set_state(PurchaseFSM.confirm_order)

        # Показываем чек
        data = await state.get_data()
        stars = data["stars"]
        price = data["price"]

        import random
        kopecks = random.randint(10, 99) / 100.0
        final_price = round(float(price) + kopecks, 2)

        receipt_text = t("order_receipt", lang,
                         order_id="—",
                         stars=stars,
                         recipient=validated,
                         price=f"{final_price:.2f}",
                         card=CARD_NUMBER,
                         holder=CARD_HOLDER,
                         jar_link=MONO_JAR_LINK)

        # Создаём заказ в БД
        order_id = await create_order(
            user_id=message.from_user.id,
            stars_amount=stars,
            price_uah=final_price,
            recipient_username=validated,
            recipient_for_self=False,
        )

        receipt_text = receipt_text.replace("#—", f"#{order_id}")
        await state.update_data(order_id=order_id)

        msg = await message.answer(
            receipt_text,
            reply_markup=payment_keyboard(lang, order_id),
            parse_mode="HTML",
        )
        await state.update_data(last_bot_msg=msg.message_id)
        await state.set_state(PurchaseFSM.confirm_order)
    except Exception as e:
        logger.error(f"Error in process_friend_username: {e}", exc_info=True)


async def _show_receipt(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    """Формирует и показывает чек с реквизитами."""
    data = await state.get_data()
    stars = data["stars"]
    price = data["price"]
    recipient = data["recipient"]

    import random
    kopecks = random.randint(10, 99) / 100.0
    final_price = round(float(price) + kopecks, 2)

    # Создаём заказ в БД
    order_id = await create_order(
        user_id=callback.from_user.id,
        stars_amount=stars,
        price_uah=final_price,
        recipient_username=recipient,
        recipient_for_self=data.get("for_self", True),
    )

    receipt_text = t("order_receipt", lang,
                     order_id=order_id,
                     stars=stars,
                     recipient=recipient,
                     price=f"{final_price:.2f}",
                     card=CARD_NUMBER,
                     holder=CARD_HOLDER,
                     jar_link=MONO_JAR_LINK)

    await state.update_data(order_id=order_id)

    await callback.message.edit_text(
        receipt_text,
        reply_markup=payment_keyboard(lang, order_id),
        parse_mode="HTML",
    )
    await state.update_data(last_bot_msg=callback.message.message_id)
    await state.set_state(PurchaseFSM.confirm_order)


# ──────────────── ОПЛАТА ────────────────

@router.callback_query(F.data.startswith("paid:"), PurchaseFSM.confirm_order)
async def callback_paid(callback: CallbackQuery, state: FSMContext) -> None:
    """Клиент нажал «Я оплатил» — просим скриншот."""
    try:
        lang = await _get_lang(callback.from_user.id)
        order_id = int(callback.data.split(":")[1])

        await callback.message.edit_text(
            t("send_screenshot", lang),
            parse_mode="HTML",
        )

        await state.set_state(PurchaseFSM.waiting_screenshot)
        await state.update_data(
            order_id=order_id,
            last_bot_msg=callback.message.message_id,
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_paid: {e}", exc_info=True)
        await callback.answer(t("error_generic", "ua"), show_alert=True)


@router.callback_query(F.data.startswith("cancel_order:"))
async def callback_cancel_order(callback: CallbackQuery, state: FSMContext) -> None:
    """Клиент отменяет заказ."""
    try:
        lang = await _get_lang(callback.from_user.id)
        order_id = int(callback.data.split(":")[1])

        await update_order_status(order_id, "cancelled", "Скасовано клієнтом")

        await callback.message.edit_text(
            t("order_cancelled_by_user", lang),
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_cancel_order: {e}", exc_info=True)


# ──────────────── СКРИНШОТ ────────────────

@router.message(PurchaseFSM.waiting_screenshot, F.photo)
async def process_screenshot(message: Message, state: FSMContext) -> None:
    """Обработка скриншота оплаты — отправка админу."""
    try:
        lang = await _get_lang(message.from_user.id)
        data = await state.get_data()
        order_id = data.get("order_id")

        if not order_id:
            await message.answer(t("error_generic", lang), parse_mode="HTML")
            await state.clear()
            return

        # Сохраняем file_id скриншота
        file_id = message.photo[-1].file_id
        await update_order_screenshot(order_id, file_id)
        await update_order_status(order_id, "paid")

        # Удаляем промежуточные сообщения
        await _delete_prev_msg(message.bot, message.chat.id, state)

        # Уведомляем клиента
        await message.answer(
            t("order_created", lang, order_id=order_id),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )

        # Отправляем уведомление админу
        from database.queries import get_order
        order = await get_order(order_id)
        user = await get_user(message.from_user.id)

        client_display = f"@{user['username']}" if user.get("username") else user.get("first_name", "Unknown")
        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        admin_text = t("admin_new_order", "ua",
                        order_id=order_id,
                        client=client_display,
                        stars=order["stars_amount"],
                        price=f"{order['price_uah']:.2f}",
                        recipient=order["recipient_username"],
                        date=now)

        # Отправляем скриншот + текст + кнопки управления
        admin_msg = await message.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=admin_text,
            reply_markup=admin_order_keyboard(order_id),
            parse_mode="HTML",
        )

        # Сохраняем ID сообщения админу
        await update_order_admin_message(order_id, admin_msg.message_id)

        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_screenshot: {e}", exc_info=True)
        lang = await _get_lang(message.from_user.id)
        await message.answer(t("error_generic", lang), parse_mode="HTML")
        await state.clear()


@router.message(PurchaseFSM.waiting_screenshot)
async def process_not_photo(message: Message, state: FSMContext) -> None:
    """Клиент отправил не фото."""
    try:
        lang = await _get_lang(message.from_user.id)
        await _delete_prev_msg(message.bot, message.chat.id, state)

        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except Exception:
            pass

        msg = await message.answer(
            t("screenshot_not_photo", lang),
            parse_mode="HTML",
        )
        await state.update_data(last_bot_msg=msg.message_id)
    except Exception as e:
        logger.error(f"Error in process_not_photo: {e}", exc_info=True)
