"""
FSM-состояния для всех пошаговых сценариев бота.
"""

from aiogram.fsm.state import State, StatesGroup


class PurchaseFSM(StatesGroup):
    """Покупка Stars — пошаговый процесс."""
    choose_package = State()        # Выбор пакета
    enter_custom_amount = State()   # Ввод своего количества
    choose_recipient = State()      # Себе / Другу
    enter_friend_username = State() # Ввод @username друга
    confirm_order = State()         # Подтверждение (чек)
    waiting_screenshot = State()    # Ожидание скриншота оплаты


class CalculatorFSM(StatesGroup):
    """Калькулятор Stars <-> UAH."""
    choose_direction = State()      # Выбор направления
    enter_amount = State()          # Ввод суммы


class ReviewFSM(StatesGroup):
    """Ввод текста отзыва."""
    enter_text = State()


class AdminSettingsFSM(StatesGroup):
    """Ввод настроек админом."""
    enter_price_100_dump = State()
    enter_price_100_standard = State()
    enter_package_price = State()


class AdminOrderFSM(StatesGroup):
    """Действия админа с конкретным заказом."""
    enter_delay_time = State()      # Ввод времени задержки
    enter_cancel_reason = State()   # Ввод причины отмены
    enter_message = State()         # Ввод сообщения клиенту
