from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.queries import add_note, list_notes
from keyboards.kbs import BTN_LIST, BTN_SEARCH, BTN_TAGS, BTN_DELETE, BTN_ADD, BTN_EDIT, BTN_EXPORT, BTN_REMIND
from utils.tags import extract_tags
from utils.formatters import format_note

router = Router()

async def show_notes_page(message_or_callback, user_id: int, page: int = 0, edit: bool = False):
    limit = 5
    offset = page * limit
    notes, total_count = await list_notes(user_id, limit=limit, offset=offset)

    if not notes:
        text = "У тебя пока нет заметок или они закончились."
        if edit:
            await message_or_callback.message.edit_text(text)
        else:
            await message_or_callback.answer(text)
        return

    lines = [f"📋 Заметки (стр. {page + 1} из {max(1, (total_count + limit - 1) // limit)}):\n"]
    for note in notes:
        lines.append(format_note(note, note['id']))
        lines.append("")

    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"page_{page - 1}")
    
    if offset + limit < total_count:
        builder.button(text="Вперед ➡️", callback_data=f"page_{page + 1}")
    
    builder.adjust(2)

    if edit:
        await message_or_callback.message.edit_text("\n".join(lines), reply_markup=builder.as_markup())
    else:
        await message_or_callback.answer("\n".join(lines), reply_markup=builder.as_markup())

@router.message(F.text == BTN_LIST)
@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    await show_notes_page(message, message.from_user.id, page=0, edit=False)

@router.callback_query(F.data.startswith("page_"))
async def process_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split("_")[1])
    await show_notes_page(callback, callback.from_user.id, page=page, edit=True)
    await callback.answer()

# ОБРАБОТКА ФОТО (только если не в режиме поиска/редактирования)
@router.message(StateFilter(None), F.photo)
async def save_photo_note(message: Message) -> None:
    file_id = message.photo[-1].file_id
    caption = message.caption or ""
    clean_text, tags = extract_tags(caption)
    
    note_id = await add_note(message.from_user.id, clean_text, tags, file_id=file_id, file_type="photo")
    tag_str = (" ".join(f"#{t}" for t in tags)) if tags else "—"
    await message.answer(f"✅ Фото-заметка #{note_id} сохранена\n🏷 Теги: {tag_str}")

# ОБРАБОТКА ДОКУМЕНТОВ
@router.message(StateFilter(None), F.document)
async def save_document_note(message: Message) -> None:
    file_id = message.document.file_id
    caption = message.caption or message.document.file_name or "Файл"
    clean_text, tags = extract_tags(caption)
    
    note_id = await add_note(message.from_user.id, clean_text, tags, file_id=file_id, file_type="document")
    tag_str = (" ".join(f"#{t}" for t in tags)) if tags else "—"
    await message.answer(f"✅ Файл-заметка #{note_id} сохранена\n🏷 Теги: {tag_str}")

# ОБРАБОТКА ТЕКСТА
@router.message(
    StateFilter(None), 
    F.text & ~F.text.startswith("/"), 
    ~F.text.in_({BTN_ADD, BTN_LIST, BTN_SEARCH, BTN_TAGS, BTN_DELETE, BTN_EDIT, BTN_EXPORT, BTN_REMIND})
)
async def save_note(message: Message) -> None:
    clean_text, tags = extract_tags(message.text)
    if not clean_text and not tags:
        return

    if not clean_text:
        await message.answer("Не могу сохранить заметку только из тегов — добавь немного текста.")
        return

    note_id = await add_note(message.from_user.id, clean_text, tags)
    tag_str = (" ".join(f"#{t}" for t in tags)) if tags else "—"
    await message.answer(f"✅ Заметка #{note_id} сохранена\n🏷 Теги: {tag_str}")

# ОБРАБОТКА ВСЕГО ОСТАЛЬНОГО (Стикеры, видео, кружочки)
@router.message(StateFilter(None), ~F.text & ~F.photo & ~F.document & ~F.voice)
async def unsupported_media(message: Message) -> None:
    await message.answer("🤷‍♂️ Я не умею обрабатывать этот тип сообщений. Отправь текст, фото, файл или голосовое.")