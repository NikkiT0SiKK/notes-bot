import dateparser
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.kbs import BTN_REMIND
from db.queries import list_notes, set_reminder, stop_repeating
from db.database import DB_PATH
from utils.formatters import format_datetime

router = Router()

class ReminderStates(StatesGroup):
    waiting_for_time = State()

@router.message(F.text == BTN_REMIND)
async def start_reminder(message: Message) -> None:
    notes, _ = await list_notes(message.from_user.id, limit=10)
    if not notes:
        await message.answer("У тебя нет заметок, к которым можно прикрепить напоминание.")
        return

    builder = InlineKeyboardBuilder()
    for note in notes:
        short_text = note['text'][:20] + "..." if len(note['text']) > 20 else note['text']
        builder.button(text=f"⏰ #{note['id']}: {short_text}", callback_data=f"remind_{note['id']}")
    
    builder.adjust(1)
    await message.answer("Выбери заметку, к которой хочешь прикрепить напоминание:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("remind_"))
async def choose_note_for_reminder(callback: CallbackQuery, state: FSMContext) -> None:
    note_id = int(callback.data.split("_")[1])
    await state.update_data(reminder_note_id=note_id)
    await state.set_state(ReminderStates.waiting_for_time)
    
    await callback.message.edit_text(
        f"Выбрана заметка #{note_id}.\n\n"
        "Когда напомнить? Напиши обычным языком:\n"
        "• <code>через 2 часа</code>\n"
        "• <code>завтра в 18:00</code>\n"
        "• <b>каждый день в 9:00</b> (для повторов)",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ReminderStates.waiting_for_time)
async def process_reminder_time(message: Message, state: FSMContext) -> None:
    user_data = await state.get_data()
    note_id = user_data.get("reminder_note_id")
    text = message.text.strip()
    text_lower = text.lower()
    
    repeat_type = None
    if "каждый день" in text_lower or "ежедневно" in text_lower:
        repeat_type = 'daily'
        text_for_parse = text_lower.replace("каждый день", "").replace("ежедневно", "").strip()
    else:
        text_for_parse = text

    dt = dateparser.parse(text_for_parse, languages=['ru'], settings={'PREFER_DATES_FROM': 'future'})
    
    if not dt:
        try:
            dt = datetime.strptime(text_for_parse, "%d.%m.%Y %H:%M")
        except ValueError:
            await message.answer("❌ Не понял время. Попробуй, например: <code>завтра в 18:00</code> или <code>каждый день в 9:00</code>", parse_mode="HTML")
            return

    if repeat_type and dt <= datetime.now():
        dt += timedelta(days=1)
    elif dt <= datetime.now():
        await message.answer("❌ Это время уже в прошлом. Введи будущую дату и время.")
        return
        
    reminder_time = dt.strftime("%Y-%m-%d %H:%M:00")
    success = await set_reminder(message.from_user.id, note_id, reminder_time, repeat_type)
    await state.clear()
    
    if success:
        repeat_msg = " (🔄 повторяется)" if repeat_type else ""
        await message.answer(
            f"✅ Напоминание для заметки #{note_id} установлено на <b>{format_datetime(reminder_time)}</b>{repeat_msg}", 
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Не удалось установить напоминание (заметка не найдена).")

@router.callback_query(F.data.startswith("snooze_"))
async def process_snooze(callback: CallbackQuery) -> None:
    note_id = int(callback.data.split("_")[1])
    new_time = datetime.now() + timedelta(minutes=10)
    reminder_time = new_time.strftime("%Y-%m-%d %H:%M:00")
    
    # Достаем текущий repeat_type, чтобы не сбросить его при откладывании
    r_type = None
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT repeat_type FROM notes WHERE id = ?", (note_id,)) as cur:
            row = await cur.fetchone()
            if row:
                r_type = row[0]

    success = await set_reminder(callback.from_user.id, note_id, reminder_time, repeat_type=r_type)
    if success:
        await callback.message.edit_text(
            f"⏰ Напоминание по заметке #{note_id} отложено на 10 минут.\n"
            f"Новое время: <b>{format_datetime(reminder_time)}</b>",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text("❌ Не удалось отложить напоминание.")
    await callback.answer("Отложено на 10 минут!")

@router.callback_query(F.data.startswith("stop_repeat_"))
async def process_stop_repeat(callback: CallbackQuery) -> None:
    note_id = int(callback.data.split("_")[2])
    await stop_repeating(note_id)
    await callback.message.edit_text(f"🛑 Повторяющееся напоминание для заметки #{note_id} остановлено.")
    await callback.answer("Повтор остановлен.")