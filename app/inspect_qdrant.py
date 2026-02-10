# inspect_qdrant.py
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

# Проверим список коллекций
collections = client.get_collections()
print("Коллекции:", [c.name for c in collections.collections])

# Посмотрим чанки пользователя 1001
from qdrant_client.models import Filter, FieldCondition, MatchValue

points, _ = client.scroll(
    collection_name="content_chunks",
    scroll_filter=Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=1001))]),
    limit=10,
    with_vectors=False
)

print(f"\nНайдено чанков для user_id=1001: {len(points)}")
for p in points:
    print(f"ID: {p.id}")
    print(f"Текст: {p.payload.get('chunk_text', '')[:60]}...")
    print(f"Кластер: {p.payload.get('cluster_label', '—')}\n")