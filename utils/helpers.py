"""
Вспомогательные функции: расчёт цен, форматирование.
"""

from __future__ import annotations
import re


def calculate_price_interpolated(stars: int, settings: dict, mode: str) -> int:
    """
    Умный расчет цены по алгоритму кусочной интерполяции на основе пакетов.
    Меньше 50 звезд покупать нельзя (обработано валидацией, но тут считаем по тарифу 50).
    """
    p50 = float(settings.get(f"price_50_{mode}", "40.0"))
    p100 = float(settings.get(f"price_100_{mode}", "80.0"))
    p250 = float(settings.get(f"price_250_{mode}", "200.0"))
    p500 = float(settings.get(f"price_500_{mode}", "400.0"))
    p1000 = float(settings.get(f"price_1000_{mode}", "800.0"))

    points = [
        (50, p50),
        (100, p100),
        (250, p250),
        (500, p500),
        (1000, p1000)
    ]

    if stars <= points[0][0]:
        return int(round((p50 / 50.0) * stars))

    for s_val, p_val in points:
        if stars == s_val:
            return int(round(p_val))

    for i in range(len(points) - 1):
        s_start, p_start = points[i]
        s_end, p_end = points[i+1]
        
        if s_start < stars < s_end:
            step = (p_end - p_start) / (s_end - s_start)
            exact_price = p_start + (stars - s_start) * step
            return int(round(exact_price))

    return int(round((p1000 / 1000.0) * stars))


def calculate_stars_from_uah_interpolated(uah: float, settings: dict, mode: str) -> int:
    """
    Обратный умный расчет: сколько Stars можно купить за uah гривен на основе интерполяции.
    """
    if uah <= 0:
        return 0

    p50 = float(settings.get(f"price_50_{mode}", "40.0"))
    p100 = float(settings.get(f"price_100_{mode}", "80.0"))
    p250 = float(settings.get(f"price_250_{mode}", "200.0"))
    p500 = float(settings.get(f"price_500_{mode}", "400.0"))
    p1000 = float(settings.get(f"price_1000_{mode}", "800.0"))

    points = [
        (50, p50),
        (100, p100),
        (250, p250),
        (500, p500),
        (1000, p1000)
    ]

    if uah < p50:
        raw = (uah / p50) * 50
        return max(0, int(round(raw)))

    for i in range(len(points) - 1):
        s_start, p_start = points[i]
        s_end, p_end = points[i+1]
        
        if p_start <= uah <= p_end:
            if p_end == p_start:
                return s_start
            step = (p_end - p_start) / (s_end - s_start)
            raw_stars = s_start + (uah - p_start) / step
            return int(round(raw_stars))

    raw = (uah / p1000) * 1000
    return int(round(raw))


def validate_username(text: str) -> str | None:
    """
    Валидирует username. Возвращает очищенный @username или None.
    Отклоняет ссылки на каналы/чаты (t.me/+... , t.me/joinchat, и т.д.).
    """
    text = text.strip()

    # Отклоняем ссылки на каналы/группы
    reject_patterns = [
        r"t\.me/\+",              # Инвайт-ссылки
        r"t\.me/joinchat",        # Старые инвайт-ссылки
        r"telegram\.me/joinchat",
        r"https?://",             # Любые ссылки
    ]
    for pattern in reject_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return None

    # Извлекаем username из текста
    # Допустимый формат: @username или просто username
    match = re.match(r"^@?([a-zA-Z][a-zA-Z0-9_]{4,31})$", text)
    if match:
        return f"@{match.group(1)}"
    return None


def get_status_emoji(status: str) -> str:
    """Возвращает эмодзи для статуса заказа."""
    return {
        "new": "⏳",
        "paid": "💸",
        "processing": "🔄",
        "delivered": "✅",
        "cancelled": "❌",
    }.get(status, "❓")


def get_mode_display(mode: str, lang: str) -> str:
    """Возвращает отображаемое название режима."""
    modes = {
        "dump": {"ua": "🔥 Демпінг", "ru": "🔥 Демпинг"},
        "standard": {"ua": "🚀 Стандарт", "ru": "🚀 Стандарт"},
    }
    return modes.get(mode, {}).get(lang, mode)
