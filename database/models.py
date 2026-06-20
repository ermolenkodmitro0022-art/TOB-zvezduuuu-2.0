"""
Схема базы данных — создание таблиц при первом запуске.
"""

import aiosqlite
from config import DB_PATH


async def init_db() -> None:
    """Создаёт все таблицы, если они ещё не существуют."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT DEFAULT '',
                first_name  TEXT DEFAULT '',
                language    TEXT DEFAULT '',
                is_banned   INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER NOT NULL,
                stars_amount        INTEGER NOT NULL,
                price_uah           REAL NOT NULL,
                recipient_username  TEXT NOT NULL DEFAULT '',
                recipient_for_self  INTEGER DEFAULT 1,
                status              TEXT NOT NULL DEFAULT 'new',
                screenshot_file_id  TEXT DEFAULT '',
                admin_message_id    INTEGER DEFAULT 0,
                cancel_reason       TEXT DEFAULT '',
                created_at          TEXT DEFAULT (datetime('now')),
                updated_at          TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id   INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                text       TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

# Значения по умолчанию для настроек
        defaults = {
            "ton_rate": "250.0",
            "markup_dump": "5.0",
            "markup_standard": "15.0",
            "active_mode": "standard",   # "dump" или "standard"
            
            # Дефолтные цены для пакетов (Стандарт)
            "price_50_standard": "40.0",
            "price_100_standard": "80.0",
            "price_250_standard": "200.0",
            "price_500_standard": "400.0",
            "price_1000_standard": "800.0",

            # Дефолтные цены для пакетов (Демпинг)
            "price_50_dump": "36.5",
            "price_100_dump": "73.0",
            "price_250_dump": "182.5",
            "price_500_dump": "365.0",
            "price_1000_dump": "730.0",
        }
