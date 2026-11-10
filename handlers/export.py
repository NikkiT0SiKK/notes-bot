from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile

from keyboards.kbs import BTN_EXPORT
from db.queries import get_all_notes

router = Router()

@router.message(F.text == BTN_EXPORT)
async def export_notes(message: Message) -> None:
    notes = await get_all_notes(message.from_user.id)
    
    if not notes:
        await message.answer("У тебя нет заметок для экспорта.")
        return

    # Формируем текст файла
    lines = ["=== МОИ ЗАМЕТКИ ===\n"]
    for note in notes:
        tags_str = " ".join(f"#{t}" for t in note['tags']) if note['tags'] else "без тегов"
        lines.append(f"#{note['id']} | {note['created_at']}")
        lines.append(f"Текст: {note['text']}")
        lines.append(f"Теги: {tags_str}")
        lines.append("-" * 20)
    
    file_content = "\n".join(lines)
    
    # Создаем файл в памяти (не сохраняя на диск)
    # Файл будет называться notes_export.txt
    document = BufferedInputFile(
        file=file_content.encode('utf-8'),
        filename="notes_export.txt"
    )
    
    await message.answer_document(
        document=document,
        caption=f"📦 Твой экспорт готов! Всего заметок: {len(notes)}"
    )