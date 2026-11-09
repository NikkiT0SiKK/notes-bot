import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")

# Ссылка на твой веб-интерфейс (Ngrok или реальный сервер)
# Если ссылки нет, по умолчанию будет заглушка
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")