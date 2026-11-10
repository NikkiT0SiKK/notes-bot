from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import aiosqlite
import hashlib
import hmac
import json
import urllib.parse
from config import BOT_TOKEN
from db.database import DB_PATH

app = FastAPI()

# Раздаем статические файлы (наш HTML)
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")

class NoteCreate(BaseModel):
    text: str

class NoteResponse(BaseModel):
    id: int
    text: str
    tags: List[str]
    created_at: str

def validate_init_data(init_data: str) -> int:
    """Проверяет подпись Telegram, чтобы убедиться, что это не хакер."""
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data))
        hash_str = parsed_data.pop('hash', None)
        if not hash_str:
            raise ValueError("No hash")
        
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash != hash_str:
            raise ValueError("Invalid hash")
            
        user_data = json.loads(parsed_data['user'])
        return user_data['id']
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid init data")

@app.get("/")
async def read_index():
    return FileResponse('webapp/static/index.html')

@app.get("/api/notes")
async def get_notes(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    user_id = validate_init_data(init_data)
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, text, created_at FROM notes WHERE user_id = ? ORDER BY id DESC", (user_id,)) as cur:
            rows = await cur.fetchall()
        
        result = []
        for row in rows:
            async with db.execute("SELECT t.name FROM tags t JOIN note_tags nt ON nt.tag_id = t.id WHERE nt.note_id = ?", (row["id"],)) as cur:
                tags = [r["name"] for r in await cur.fetchall()]
            result.append({"id": row["id"], "text": row["text"], "created_at": row["created_at"], "tags": tags})
        return result

@app.post("/api/notes")
async def create_note(note: NoteCreate, request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    user_id = validate_init_data(init_data)
    
    import re
    tags = [t.lower() for t in re.findall(r"#(\w+)", note.text)]
    clean_text = re.sub(r"#(\w+)", "", note.text).strip()
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO notes (user_id, text) VALUES (?, ?)", (user_id, clean_text))
        note_id = cursor.lastrowid
        for tag in tags:
            await db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            async with db.execute("SELECT id FROM tags WHERE name = ?", (tag,)) as cur:
                tag_id = (await cur.fetchone())[0]
            await db.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))
        await db.commit()
        return {"status": "ok", "id": note_id}

@app.delete("/api/notes/{note_id}")
async def delete_note_api(note_id: int, request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    user_id = validate_init_data(init_data)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        await db.commit()
        return {"status": "ok"}