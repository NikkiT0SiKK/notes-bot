from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.kbs import BTN_DELETE
from db.queries import list_notes, delete_note

router = Router()


@router.message(F.text == BTN_DELETE)
async def start_delete(message: Message) -> None:
    notes, _ = await list_notes(message.from_user.id, limit=10)
    
    if not notes:
        await message.answer("У тебя нет заметок, которые можно было бы удалить.")
        return

    builder = InlineKeyboardBuilder()
    for note in notes:
        short_text = note['text'][:20] + "..." if len(note['text']) > 20 else note['text']
        builder.button(text=f"🗑 #{note['id']}: {short_text}", callback_data=f"del_{note['id']}")
    
    builder.adjust(1)
    await message.answer("Выбери заметку, которую хочешь удалить:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("del_"))
async def ask_delete_confirm(callback: CallbackQuery) -> None:
    # Достаем ID заметки
    note_id = int(callback.data.split("_")[1])
    
    builder = InlineKeyboardBuilder()
    # Создаем кнопки подтверждения
    builder.button(text="✅ Да, удалить", callback_data=f"confirm_del_{note_id}")
    builder.button(text="❌ Отмена", callback_data="cancel_del")
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"Ты уверен, что хочешь удалить заметку #{note_id}?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_del_"))
async def process_delete(callback: CallbackQuery) -> None:
    note_id = int(callback.data.split("_")[2])
    success = await delete_note(callback.from_user.id, note_id)
    
    if success:
        await callback.message.edit_text(f"✅ Заметка #{note_id} успешно удалена.")
    else:
        await callback.message.edit_text("❌ Заметка не найдена или уже была удалена.")
        
    await callback.answer()


@router.callback_query(F.data == "cancel_del")
async def cancel_delete(callback: CallbackQuery) -> None:
    # Просто удаляем сообщение с вопросом
    await callback.message.delete()
    await callback.answer("Удаление отменено.")