from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct, VectorParams, Distance, CollectionConfig
)
from typing import List, Dict, Any, Optional
import uuid
from app.settings.db_credentials import *


class QdrantManager:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = qdrant_collection_name
        self._ensure_collection_exists()  # ← вызывается здесь!

    def _ensure_collection_exists(self):
        """Создаёт коллекцию при первом запуске"""
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": VectorParams(size=384, distance=Distance.COSINE)
                }
            )
            print(f"✅ Коллекция '{self.collection_name}' создана")

    # В app/qdrant_manager.py
    def save_chunks(self, chunks_data: List[Dict[str, Any]]) -> List[str]:
        points = []
        for item in chunks_data:
            # Извлекаем dense и sparse (если есть)
            dense_vector = item.pop("dense_vector")
            sparse_vector = item.pop("sparse_vector", None)  # ← заглушка
            
            # Формируем multi-vector
            vector = {"dense": dense_vector}
            if sparse_vector is not None:
                vector["sparse"] = sparse_vector
            
            point_id = item["chunk_id"]
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload=item
            ))

        self.client.upsert(collection_name=self.collection_name, points=points)
        return [p.id for p in points]

    def search(self, query_vector: List[float], user_id: Optional[int] = None, limit: int = 5):
        """Поиск по dense-вектору с опциональной фильтрацией по пользователю"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = None
        if user_id is not None:
            query_filter = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            )

        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit
        )

    def get_document_chunks(self, content_id: int, user_id: int) -> List[Dict]:
        """Получить все чанки документа для сборки полного текста"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue, ScrollRequest

        scroll_filter = Filter(
            must=[
                FieldCondition(key="content_id", match=MatchValue(value=content_id)),
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]
        )

        hits, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=scroll_filter,
            limit=100
        )
        return [{"id": h.id, "payload": h.payload} for h in hits]
    
    # В QdrantManager
    def hybrid_search(
        self,
        dense_query: List[float],
        sparse_query: Optional[Dict] = None,
        user_id: Optional[int] = None,
        limit: int = 5,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3
    ):
        """
        Заглушка под гибридный поиск.
        Пока возвращает только dense-результаты.
        """
        if sparse_query is None:
            # Только dense-поиск (текущая логика)
            return self.search(dense_query, user_id=user_id, limit=limit)
        
        # TODO: Реализовать комбинацию dense + sparse
        # Например: rerank или weighted fusion
        raise NotImplementedError("Гибридный поиск пока не реализован")