from sentence_transformers import SentenceTransformer
from typing import List, Literal
from app.settings.models import *

class Embedder:
    def __init__(self, model_name: str = transformer_model_name):
        print("🔍 Загружаем модель эмбеддингов...")
        self.model = SentenceTransformer(model_name, device="cpu")
        print("✅ Модель загружена.")

    def embed(self, texts: List[str], emb_type: Literal["query", "passage"] = "query") -> List[List[float]]:
        # Добавляем префикс согласно рекомендациям E5
        prefix = "query: " if emb_type == "query" else "passage: "
        prefixed = [prefix + t for t in texts]
        # Нормализуем — обязательно для семантического поиска (cosine similarity = dot)
        embeddings = self.model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()  # JSON-сериализуемый список списков