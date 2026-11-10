import asyncio
import logging
import uvicorn
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN
from db.database import init_db
from db.queries import get_due_reminders, mark_as_reminded

# Импортируем роутеры
from handlers import notes, search, tags, delete, edit, export, reminders
from keyboards.kbs import main_menu

# Импортируем наше FastAPI приложение
from webapp.api import app as fastapi_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
dp = Dispatcher()

# Подключаем роутеры
dp.include_router(notes.router)
dp.include_router(search.router)
dp.include_router(tags.router)
dp.include_router(delete.router)
dp.include_router(edit.router)
dp.include_router(export.router)
dp.include_router(reminders.router)

# Безопасное подключение голосового роутера
try:
    from handlers import voice
    dp.include_router(voice.router)
except Exception as e:
    logging.error(f"Не удалось загрузить голосовой модуль: {e}")


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 <b>Привет! Я твой умный помощник для заметок.</b>\n\n"
        "Теперь у меня есть красивый веб-интерфейс! Нажми на кнопку <b>🌐 Веб-интерфейс</b> внизу, чтобы открыть его.\n\n"
        "📌 <b>Что я еще умею:</b>\n"
        "• Сохранять текст, фото и голосовые\n"
        "• Ставить умные напоминания\n"
        "• Экспортировать всё в файл\n\n"
        "Нажми /help, чтобы узнать больше.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Справка по командам</b>\n\n"
        "🔹 <b>Кнопки меню:</b>\n"
        "🌐 <b>Веб-интерфейс</b> — открыть красивое приложение\n"
        "➕ <b>Добавить</b> — сохранить новую заметку текстом\n"
        "📋 <b>Список</b> — показать последние заметки с листалкой\n"
        "🔍 <b>Поиск</b> — умный поиск по смыслу или #тегу\n"
        "🏷 <b>Теги</b> — показать все твои теги\n"
        "✏️ <b>Изменить</b> — переписать текст заметки\n"
        "🗑 <b>Удалить</b> — стереть заметку\n"
        "💾 <b>Экспорт</b> — получить все заметки в .txt файле\n"
        "⏰ <b>Напоминания</b> — поставить дедлайн к заметке\n\n"
        "💡 <b>Совет:</b> Отправь голосовое сообщение, и я переведу его в текст!",
        parse_mode="HTML",
    )


async def reminder_worker(bot: Bot):
    logging.info("Фоновый процесс напоминаний запущен.")
    while True:
        try:
            due_reminders = await get_due_reminders()
            for note in due_reminders:
                user_id = note["user_id"]
                note_id = note["id"]
                text = note["text"]
                repeat_type = note["repeat_type"]
                file_id = note["file_id"]
                file_type = note["file_type"]
                
                builder = InlineKeyboardBuilder()
                builder.button(text="⏰ Отложить на 10 минут", callback_data=f"snooze_{note_id}")
                if repeat_type:
                    builder.button(text="🛑 Остановить повтор", callback_data=f"stop_repeat_{note_id}")
                builder.adjust(1)
                
                if file_id:
                    caption = f"🔔 <b>НАПОМИНАНИЕ</b>\n\n{text}"
                    if file_type == "photo":
                        await bot.send_photo(user_id, file_id, caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML")
                    else:
                        await bot.send_document(user_id, file_id, caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML")
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"🔔 <b>НАПОМИНАНИЕ</b> 🔔\n\nЗаметка #{note_id}:\n{text}",
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
                
                await mark_as_reminded(note_id, repeat_type)
                
        except Exception as e:
            logging.error(f"Ошибка в фоновом процессе напоминаний: {e}")
            
        await asyncio.sleep(30)


async def main() -> None:
    # 1. Инициализируем базу данных
    await init_db()
    
    # 2. Запускаем FastAPI (веб-сервер) в фоне
    # Render автоматически передает нужный порт в переменную PORT
    port = int(os.environ.get("PORT", 8000))
    logging.info(f"Запуск веб-сервера на порту {port}...")
    
    uvicorn_config = uvicorn.Config(
        fastapi_app, 
        host="0.0.0.0", 
        port=port, 
        log_level="warning"
    )
    server = uvicorn.Server(uvicorn_config)
    asyncio.create_task(server.serve())
    
    # 3. Создаем бота и запускаем фоновые задачи
    bot = Bot(token=BOT_TOKEN)
    asyncio.create_task(reminder_worker(bot))
    
    logging.info("Бот запущен, начинаю polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")