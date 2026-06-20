"""
Точка входа — запуск Telegram-бота.
Инициализация Bot, Dispatcher, подключение роутеров и middleware.
"""

import asyncio
import logging
import sys
import threading  # Добавили для работы в фоне

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import streamlit as st  # Добавили для Hugging Face

from config import BOT_TOKEN
from database.models import init_db
from middlewares.ban_check import BanCheckMiddleware

# Импорт роутеров
from handlers.start import router as start_router
from handlers.menu import router as menu_router
from handlers.purchase import router as purchase_router
from handlers.calculator import router as calculator_router
from handlers.reviews import router as reviews_router
from handlers.admin import router as admin_router

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция запуска бота."""

    # ── Валидация конфигурации ──
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error("❌ BOT_TOKEN не задан! Заполните .env файл.")
        sys.exit(1)

    # ── Инициализация БД ──
    logger.info("📦 Инициализация базы данных...")
    await init_db()
    logger.info("✅ База данных готова.")

    # ── Создание бота и диспетчера ──
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # ── Подключение middleware ──
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    # ── Регистрация роутеров (порядок важен!) ──
    dp.include_routers(
        start_router,      # /start — первым
        admin_router,       # /admin и управление заказами
        purchase_router,    # Покупка Stars (FSM)
        calculator_router,  # Калькулятор
        reviews_router,     # Отзывы
        menu_router,        # Главное меню — последним (ловит текстовые кнопки)
    )

    # ── Запуск ──
    logger.info("🚀 Бот запускается...")
    try:
        # Удаляем webhook (на случай, если был) и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("🛑 Бот остановлен.")


# ── СЕКЦИЯ ДЛЯ HUGGING FACE SPACES ──

# Простой красивый интерфейс, который будет видеть Hugging Face
st.set_page_config(page_title="StarPulse Server", page_icon="⭐")
st.title("🤖 StarPulse Bot Server")
st.markdown("---")
st.success("✅ Сервер активен. Бот успешно запущен в фоновом режиме и работает 24/7!")
st.info("Вы можете закрыть эту страницу, бот продолжит работу.")


# Функция для запуска асинхронного main() в отдельном потоке
def run_async_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Ошибка в работе бота: {e}")


# Кэшируем запуск, чтобы поток создался ОДИН раз для всех пользователей сайта
@st.cache_resource
def start_bot_thread():
    logger.info("⏳ Запуск потока с Telegram ботом...")
    thread = threading.Thread(target=run_async_bot, daemon=True)
    thread.start()
    return "Бот работает"


if __name__ == "__main__":
    # Запускаем фоновый поток через кэш Streamlit
    start_bot_thread()