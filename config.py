"""
Конфигурация бота — загрузка переменных окружения из .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))
CARD_NUMBER: str = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")
CARD_HOLDER: str = os.getenv("CARD_HOLDER", "Невідомо")
MONO_JAR_LINK: str = os.getenv("MONO_JAR_LINK", "")

# Пакеты Stars для быстрого выбора
STAR_PACKAGES: list[int] = [50, 100, 200, 250, 500, 1000]

# Минимальное и максимальное количество Stars для ручного ввода
MIN_STARS: int = 50
MAX_STARS: int = 50000

# Путь к файлу базы данных
DB_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_database.db")
