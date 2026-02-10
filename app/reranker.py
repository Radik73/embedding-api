# app/reranker.py
from sentence_transformers import CrossEncoder
from app.settings.models import *
import os


class Reranker:
    def __init__(self):
        print("🔍 Загружаем модель reranking...")
        # Для мультиязычного reranking (включая русский)
        self.model = CrossEncoder(
            reranked_model,
            max_length=512
        )
        print("✅ Модель reranking загружена")

    def rerank(self, query: str, documents: list[str], top_k: int = None) -> list[tuple[float, str]]:
        if not documents:
            return []
        
        pairs = [(query, doc) for doc in documents]
        scores = self.model.predict(pairs, batch_size=32)
        
        # Конвертируем numpy.float32 → float
        scored_docs = [(float(score), doc) for score, doc in zip(scores, documents)]
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        if top_k:
            scored_docs = scored_docs[:top_k]
            
        return scored_docs