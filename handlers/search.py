from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from db.queries import search_notes
from keyboards.kbs import BTN_SEARCH
from utils.formatters import format_note

router = Router()

class SearchStates(StatesGroup):
    waiting_for_query = State()

@router.message(F.text == BTN_SEARCH)
async def start_search(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_for_query)
    await message.answer("🔍 Введи слово или #тег для поиска:")

@router.message(Command("search"))
async def cmd_search(message: Message) -> None:
    query = message.text.replace("/search", "").strip()
    if not query:
        await message.answer("Напиши так: <code>/search молоко</code>", parse_mode="HTML")
        return
    await _perform_search(message, query)

@router.message(SearchStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _perform_search(message, message.text)

async def _perform_search(message: Message, query: str) -> None:
    notes = await search_notes(message.from_user.id, query)
    
    if not notes:
        await message.answer(f"🔍 По запросу «{query}» ничего не найдено.")
        return

    lines = [f"🔍 Результаты по запросу «{query}» ({len(notes)}):\n"]
    for note in notes:
        lines.append(format_note(note, note['id']))
        lines.append("")
    await message.answer("\n".join(lines))