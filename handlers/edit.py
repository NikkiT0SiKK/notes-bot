from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.kbs import BTN_EDIT
from db.queries import list_notes, update_note
from utils.tags import extract_tags

router = Router()

class EditStates(StatesGroup):
    waiting_for_new_text = State()

@router.message(F.text == BTN_EDIT)
async def start_edit(message: Message) -> None:
    # Берем 10 последних заметок
    notes, _ = await list_notes(message.from_user.id, limit=10)
    
    if not notes:
        await message.answer("Тебе нечего редактировать — заметок пока нет.")
        return

    builder = InlineKeyboardBuilder()
    for note in notes:
        short_text = note['text'][:20] + "..." if len(note['text']) > 20 else note['text']
        builder.button(text=f"✏️ #{note['id']}: {short_text}", callback_data=f"edit_{note['id']}")
    
    builder.adjust(1)
    await message.answer("Выбери заметку для редактирования:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("edit_"))
async def choose_note_to_edit(callback: CallbackQuery, state: FSMContext) -> None:
    note_id = int(callback.data.split("_")[1])
    
    # Сохраняем ID заметки в состояние
    await state.update_data(edit_note_id=note_id)
    await state.set_state(EditStates.waiting_for_new_text)
    
    await callback.message.edit_text(f"Отправь новый текст для заметки #{note_id}.\n(Не забудь указать теги, если они нужны, например: Купить хлеб #еда)")
    await callback.answer()

@router.message(EditStates.waiting_for_new_text)
async def process_new_text(message: Message, state: FSMContext) -> None:
    # Достаем ID заметки из состояния
    user_data = await state.get_data()
    note_id = user_data.get("edit_note_id")
    
    # Очищаем состояние
    await state.clear()
    
    if not note_id:
        await message.answer("Что-то пошло не так. Попробуй начать редактирование заново.")
        return

    # Парсим новый текст и теги
    clean_text, tags = extract_tags(message.text)
    
    if not clean_text:
        await message.answer("Текст заметки не может быть пустым.")
        return

    # Обновляем в БД
    success = await update_note(message.from_user.id, note_id, clean_text, tags)
    
    if success:
        tag_str = (" ".join(f"#{t}" for t in tags)) if tags else "—"
        await message.answer(f"✅ Заметка #{note_id} успешно обновлена!\n🏷 Новые теги: {tag_str}")
    else:
        await message.answer("❌ Не удалось обновить заметку (возможно, она была удалена).")