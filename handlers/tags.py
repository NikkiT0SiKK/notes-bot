from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.kbs import BTN_TAGS
from db.queries import get_user_tags, search_notes
from utils.formatters import format_note

router = Router()

@router.message(F.text == BTN_TAGS)
async def show_tags(message: Message) -> None:
    tags = await get_user_tags(message.from_user.id)
    
    if not tags:
        await message.answer("У тебя пока нет тегов. Добавь их в текст заметки, например: <code>Купить хлеб #еда</code>", parse_mode="HTML")
        return

    if len(tags) > 30:
        tags = tags[:30]
        await message.answer("⚠️ У тебя очень много тегов, показаны первые 30.")

    builder = InlineKeyboardBuilder()
    for tag in tags:
        builder.button(text=f"#{tag}", callback_data=f"tag_{tag}")
    
    builder.adjust(2)

    await message.answer(
        "🏷 Твои теги (нажми на любой, чтобы отфильтровать заметки):",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("tag_"))
async def filter_by_tag(callback: CallbackQuery) -> None:
    tag = callback.data.split("_", 1)[1]
    notes = await search_notes(callback.from_user.id, tag)
    
    if not notes:
        await callback.message.answer(f"По тегу #{tag} ничего не найдено.")
        await callback.answer()
        return

    lines = [f"🏷 Заметки с тегом #{tag} ({len(notes)}):\n"]
    for note in notes:
        lines.append(format_note(note, note['id']))
        lines.append("")
        
    await callback.message.answer("\n".join(lines))
    await callback.answer()