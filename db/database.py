import aiosqlite

DB_PATH = "notes.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    text       TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS note_tags (
    note_id INTEGER NOT NULL,
    tag_id  INTEGER NOT NULL,
    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)  REFERENCES tags(id)  ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id);
"""

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        
        # Миграции (добавляем колонки, если их нет)
        async with db.execute("PRAGMA table_info(notes)") as cur:
            columns = [col[1] for col in await cur.fetchall()]
        
        if "reminder_at" not in columns:
            await db.execute("ALTER TABLE notes ADD COLUMN reminder_at TEXT")
        if "reminded" not in columns:
            await db.execute("ALTER TABLE notes ADD COLUMN reminded INTEGER DEFAULT 0")
        if "file_id" not in columns:
            await db.execute("ALTER TABLE notes ADD COLUMN file_id TEXT")
        if "file_type" not in columns:
            await db.execute("ALTER TABLE notes ADD COLUMN file_type TEXT")
        if "repeat_type" not in columns:
            await db.execute("ALTER TABLE notes ADD COLUMN repeat_type TEXT") # 'daily', 'weekly'
            
        await db.commit()