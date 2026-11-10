import asyncio
import logging
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Загружаем модель один раз при старте (ленивая инициализация)
_model = None
_client = None
COLLECTION_NAME = "notes_semantic"

def get_model():
    global _model
    if _model is None:
        logger.info("Загрузка модели эмбеддингов rubert-tiny-sts-v2...")
        _model = SentenceTransformer('sergeyzh/rubert-tiny-sts-v2')
        logger.info("Модель загружена.")
    return _model

def get_chroma_client():
    global _client
    if _client is None:
        _client = PersistentClient(path="./chroma_data")
    return _client

def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # Используем косинусное сходство
    )

async def _add_embedding_sync(note_id: int, text: str):
    """Синхронная функция для добавления в Chroma (выполняется в отдельном потоке)."""
    model = get_model()
    collection = get_collection()
    embedding = model.encode(text).tolist()
    collection.upsert(
        ids=[str(note_id)],
        embeddings=[embedding],
        documents=[text]
    )

async def add_note_to_index(note_id: int, text: str):
    """Асинхронно добавляет или обновляет эмбеддинг заметки."""
    await asyncio.to_thread(_add_embedding_sync, note_id, text)

async def _delete_embedding_sync(note_id: int):
    collection = get_collection()
    collection.delete(ids=[str(note_id)])

async def delete_note_from_index(note_id: int):
    """Удаляет эмбеддинг заметки из индекса."""
    await asyncio.to_thread(_delete_embedding_sync, note_id)

async def _search_embeddings_sync(query: str, top_k: int = 10):
    model = get_model()
    collection = get_collection()
    query_embedding = model.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    # Возвращаем список кортежей (id, расстояние)
    if results['ids'] and results['ids'][0]:
        ids = [int(id_) for id_ in results['ids'][0]]
        distances = results['distances'][0] if results['distances'] else [0.0] * len(ids)
        return list(zip(ids, distances))
    return []

async def semantic_search(query: str, top_k: int = 10) -> list[tuple[int, float]]:
    """Возвращает список (note_id, score) наиболее релевантных заметок."""
    return await asyncio.to_thread(_search_embeddings_sync, query, top_k)

async def rebuild_index_for_user(notes: list[dict]):
    """Переиндексирует все заметки пользователя (для миграции существующих данных)."""
    # Эта функция может быть вызвана при первом запуске, если индекс пуст
    for note in notes:
        await add_note_to_index(note['id'], note['text'])