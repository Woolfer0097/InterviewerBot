from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_answer_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Создает inline клавиатуру с кнопками 'Подсказка' и 'Меню'."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💡 Подсказка", callback_data=f"hint:{question_id}"),
            InlineKeyboardButton(text="📋 Меню", callback_data=f"menu:{question_id}")
        ]
    ])
    return keyboard


def get_feedback_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Создает inline клавиатуру с кнопкой 'Получить фидбек'."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Получить фидбек", callback_data=f"feedback:{question_id}")]
    ])
    return keyboard


def get_edit_answer_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Создает inline клавиатуру с кнопками 'Изменить ответ' и 'Оставить ответ'."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Изменить ответ", callback_data=f"edit:{question_id}"),
            InlineKeyboardButton(text="✅ Оставить ответ", callback_data=f"keep:{question_id}")
        ]
    ])
    return keyboard

