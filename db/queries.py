import aiosqlite
from datetime import datetime, timedelta
from db.database import DB_PATH

async def add_note(user_id: int, text: str, tags: list[str], file_id: str = None, file_type: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO notes (user_id, text, file_id, file_type) VALUES (?, ?, ?, ?)", 
            (user_id, text, file_id, file_type)
        )
        note_id = cursor.lastrowid
        for tag in tags:
            await db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            async with db.execute("SELECT id FROM tags WHERE name = ?", (tag,)) as cur:
                row = await cur.fetchone()
                tag_id = row[0]
            await db.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))
        await db.commit()
        return note_id

async def list_notes(user_id: int, limit: int = 5, offset: int = 0) -> tuple[list[dict], int]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) FROM notes WHERE user_id = ?", (user_id,)) as cur:
            total_count = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT id, text, created_at, reminder_at, repeat_type, file_id, file_type FROM notes WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?", 
            (user_id, limit, offset)
        ) as cur:
            rows = await cur.fetchall()
        result = []
        for row in rows:
            async with db.execute("SELECT t.name FROM tags t JOIN note_tags nt ON nt.tag_id = t.id WHERE nt.note_id = ? ORDER BY t.name", (row["id"],)) as cur:
                tag_rows = await cur.fetchall()
            result.append(dict(row, tags=[r["name"] for r in tag_rows]))
        return result, total_count

async def search_notes(user_id: int, query: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = """
            SELECT DISTINCT n.id, n.text, n.created_at, n.reminder_at, n.repeat_type, n.file_id, n.file_type
            FROM notes n
            LEFT JOIN note_tags nt ON nt.note_id = n.id
            LEFT JOIN tags t ON t.id = nt.tag_id
            WHERE n.user_id = ? AND (n.text LIKE ? OR t.name LIKE ?)
            ORDER BY n.id DESC LIMIT 20
        """
        clean_query = query.strip('#').strip()
        pattern = f"%{clean_query}%"
        async with db.execute(sql, (user_id, pattern, pattern)) as cur:
            rows = await cur.fetchall()
        result = []
        for row in rows:
            async with db.execute("SELECT t.name FROM tags t JOIN note_tags nt ON nt.tag_id = t.id WHERE nt.note_id = ? ORDER BY t.name", (row["id"],)) as cur:
                tag_rows = await cur.fetchall()
            result.append(dict(row, tags=[r["name"] for r in tag_rows]))
        return result

async def get_user_tags(user_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT DISTINCT t.name FROM tags t JOIN note_tags nt ON nt.tag_id = t.id JOIN notes n ON n.id = nt.note_id WHERE n.user_id = ? ORDER BY t.name", (user_id,)) as cur:
            rows = await cur.fetchall()
        return [row[0] for row in rows]

async def cleanup_tags() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM note_tags)")
        await db.commit()

async def delete_note(user_id: int, note_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        await db.commit()
        if cursor.rowcount > 0:
            await cleanup_tags()
        return cursor.rowcount > 0

async def update_note(user_id: int, note_id: int, new_text: str, new_tags: list[str]) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)) as cur:
            if not await cur.fetchone():
                return False
        await db.execute("UPDATE notes SET text = ?, updated_at = datetime('now') WHERE id = ?", (new_text, note_id))
        await db.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
        for tag in new_tags:
            await db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            async with db.execute("SELECT id FROM tags WHERE name = ?", (tag,)) as cur:
                tag_id = (await cur.fetchone())[0]
            await db.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))
        await db.commit()
        await cleanup_tags()
        return True

async def get_all_notes(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, text, created_at, reminder_at FROM notes WHERE user_id = ? ORDER BY id ASC", (user_id,)) as cur:
            rows = await cur.fetchall()
        result = []
        for row in rows:
            async with db.execute("SELECT t.name FROM tags t JOIN note_tags nt ON nt.tag_id = t.id WHERE nt.note_id = ? ORDER BY t.name", (row["id"],)) as cur:
                tag_rows = await cur.fetchall()
            result.append(dict(row, tags=[r["name"] for r in tag_rows]))
        return result

# --- ФУНКЦИИ ДЛЯ НАПОМИНАНИЙ ---

async def set_reminder(user_id: int, note_id: int, reminder_time: str, repeat_type: str = None) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE notes SET reminder_at = ?, reminded = 0, repeat_type = ? WHERE id = ? AND user_id = ?", 
            (reminder_time, repeat_type, note_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0

async def get_due_reminders() -> list[dict]:
    """Возвращает список заметок, время напоминания которых наступило."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, text, repeat_type, file_id, file_type FROM notes WHERE reminder_at <= datetime('now') AND reminded = 0 AND reminder_at IS NOT NULL"
        ) as cur:
            return await cur.fetchall()

async def mark_as_reminded(note_id: int, repeat_type: str = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        if repeat_type == 'daily':
            await db.execute("UPDATE notes SET reminder_at = datetime(reminder_at, '+1 day'), reminded = 0 WHERE id = ?", (note_id,))
        elif repeat_type == 'weekly':
            await db.execute("UPDATE notes SET reminder_at = datetime(reminder_at, '+7 days'), reminded = 0 WHERE id = ?", (note_id,))
        else:
            await db.execute("UPDATE notes SET reminded = 1 WHERE id = ?", (note_id,))
        await db.commit()

async def stop_repeating(note_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE notes SET repeat_type = NULL, reminded = 1 WHERE id = ?", (note_id,))
        await db.commit()