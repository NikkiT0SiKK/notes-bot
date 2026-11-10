from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from config import WEBAPP_URL

BTN_ADD = "➕ Добавить"
BTN_LIST = "📋 Список"
BTN_SEARCH = "🔍 Поиск"
BTN_TAGS = "🏷 Теги"
BTN_DELETE = "🗑 Удалить"
BTN_EDIT = "✏️ Изменить"
BTN_EXPORT = "💾 Экспорт"
BTN_REMIND = "⏰ Напоминания"
BTN_WEBAPP = "🌐 Веб-интерфейс"

def main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            # Кнопка веб-приложения на самом видном месте
            [KeyboardButton(text=BTN_WEBAPP, web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text=BTN_ADD), KeyboardButton(text=BTN_LIST)],
            [KeyboardButton(text=BTN_SEARCH), KeyboardButton(text=BTN_TAGS)],
            [KeyboardButton(text=BTN_EDIT), KeyboardButton(text=BTN_DELETE)],
            [KeyboardButton(text=BTN_EXPORT), KeyboardButton(text=BTN_REMIND)],
        ],
        resize_keyboard=True,
    )
    return kb