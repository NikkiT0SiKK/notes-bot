from datetime import datetime

def format_datetime(dt_str: str | None) -> str:
    if not dt_str:
        return ""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return dt_str

def format_note(note: dict, index: int | None = None) -> str:
    prefix = f"#{index}. " if index is not None else ""
    tags = " ".join(f"#{t}" for t in note["tags"])
    
    # Обрезаем текст, если он слишком длинный, чтобы не сломать сообщение Telegram
    display_text = note['text']
    if len(display_text) > 100:
        display_text = display_text[:100] + "..."
        
    file_marker = "📎 [Вложение] " if note.get("file_id") else ""
    
    line = f"{prefix}{file_marker}{display_text}"
    if tags:
        line += f"\n   🏷 {tags}"
    
    if note.get("reminder_at"):
        repeat_icon = "🔄 " if note.get("repeat_type") else "⏰ "
        line += f"\n   {repeat_icon}{format_datetime(note['reminder_at'])}"
        
    line += f"\n   🕒 {format_datetime(note['created_at'])}"
    return line