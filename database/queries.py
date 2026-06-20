"""
Асинхронные запросы к базе данных.
Все функции — async, подключаются через aiosqlite.
"""

from __future__ import annotations
from typing import Any, Optional
import aiosqlite
from config import DB_PATH


# ─────────────────────────────── USERS ───────────────────────────────

async def get_user(user_id: int) -> Optional[dict]:
    """Возвращает пользователя по ID или None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(
    user_id: int,
    username: str = "",
    first_name: str = "",
    language: str = "",
) -> None:
    """Создаёт нового пользователя (игнорирует, если уже есть)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users (user_id, username, first_name, language)
               VALUES (?, ?, ?, ?)""",
            (user_id, username, first_name, language),
        )
        await db.commit()


async def update_language(user_id: int, language: str) -> None:
    """Обновляет язык пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET language = ? WHERE user_id = ?",
            (language, user_id),
        )
        await db.commit()


async def update_username(user_id: int, username: str, first_name: str) -> None:
    """Обновляет username и first_name пользователя при каждом обращении."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
            (username, first_name, user_id),
        )
        await db.commit()


async def ban_user(user_id: int) -> None:
    """Заносит пользователя в чёрный список."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def unban_user(user_id: int) -> None:
    """Убирает пользователя из чёрного списка."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def is_banned(user_id: int) -> bool:
    """Проверяет, забанен ли пользователь."""
    user = await get_user(user_id)
    return bool(user and user["is_banned"])


# ─────────────────────────────── ORDERS ──────────────────────────────

async def create_order(
    user_id: int,
    stars_amount: int,
    price_uah: float,
    recipient_username: str,
    recipient_for_self: bool = True,
) -> int:
    """Создаёт новый заказ и возвращает его ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO orders
               (user_id, stars_amount, price_uah, recipient_username, recipient_for_self)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, stars_amount, price_uah, recipient_username, int(recipient_for_self)),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def get_order(order_id: int) -> Optional[dict]:
    """Возвращает заказ по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_order_status(
    order_id: int,
    status: str,
    cancel_reason: str = "",
) -> None:
    """Обновляет статус заказа."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE orders
               SET status = ?, cancel_reason = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (status, cancel_reason, order_id),
        )
        await db.commit()


async def update_order_screenshot(order_id: int, file_id: str) -> None:
    """Сохраняет file_id скриншота оплаты."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE orders
               SET screenshot_file_id = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (file_id, order_id),
        )
        await db.commit()


async def update_order_admin_message(order_id: int, message_id: int) -> None:
    """Сохраняет ID сообщения админу для дальнейшего редактирования."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET admin_message_id = ? WHERE id = ?",
            (message_id, order_id),
        )
        await db.commit()


async def get_user_orders(user_id: int, limit: int = 20) -> list[dict]:
    """Возвращает список заказов пользователя (новые первыми)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM orders
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_active_order(user_id: int) -> Optional[dict]:
    """Возвращает активный (незакрытый) заказ пользователя, если есть."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM orders
               WHERE user_id = ? AND status NOT IN ('delivered', 'cancelled')
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ─────────────────────────────── SETTINGS ────────────────────────────

async def get_setting(key: str) -> str:
    """Возвращает значение настройки."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""


async def set_setting(key: str, value: str) -> None:
    """Устанавливает значение настройки."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()


async def get_all_settings() -> dict[str, str]:
    """Возвращает все настройки как словарь."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM settings") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


# ─────────────────────────────── REVIEWS ─────────────────────────────

async def save_review(order_id: int, user_id: int, text: str) -> int:
    """Сохраняет отзыв клиента."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reviews (order_id, user_id, text) VALUES (?, ?, ?)",
            (order_id, user_id, text),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def get_reviews(limit: int = 10) -> list[dict]:
    """Возвращает последние отзывы."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT r.*, u.username, u.first_name
               FROM reviews r
               JOIN users u ON r.user_id = u.user_id
               ORDER BY r.created_at DESC
               LIMIT ?""",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def count_completed_orders() -> int:
    """Подсчитывает количество выполненных заказов."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'delivered'"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
