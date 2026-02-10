# from app.postgres_processor import PostgresProcessor
# from app.embedder import Embedder
# from typing import List, Dict, Any, Optional, Literal
# from app.chunker import semantic_chunk
# import uuid
# import hashlib
# from app.qdrant_manager import QdrantManager
# from app.cluster_utils import cosine_similarity


# class ContentProcessor:
#     def __init__(self, embedder: Embedder, postgres_processor: Optional[PostgresProcessor] = None):
#         self.embedder = embedder
#         self.postgres_processor = postgres_processor

#     def generate_content_id(self, **kwargs) -> int:
#         """
#         Генерирует уникальный числовой ID документа.
#         Использует UUID для гарантии уникальности, затем преобразует в int.
#         """
#         # Генерируем UUID4 (случайный, криптостойкий)
#         unique_id = uuid.uuid4()
#         # Преобразуем в целое число (максимум 128 бит → умещается в BIGINT PostgreSQL)
#         content_id = int(unique_id.int % (10 ** 16))  # ограничим до 16 цифр для безопасности
#         return content_id


#     def process_and_save(
#         self,
#         text: str,
#         qdrant_manager: QdrantManager,
#         chunk_size: int = 2000,
#         overlap: int = 200,
#         emb_type: str = "passage",
#         **kwargs
#     ) -> Dict[str, Any]:
#         clean_text = text.strip()
#         user_id = kwargs.get("user_id", 0)
#         content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
#         point_ids = []

#         # Проверка дубликата
#         if self.postgres_processor:
#             existing_id = self.postgres_processor.get_content_id_by_hash(user_id, content_hash)
#             if existing_id is not None:
#                 return {
#                     "content_id": existing_id,
#                     "saved_chunks": len(point_ids),
#                     "status": "duplicates",
#                     "user_id": kwargs.get("user_id", 0),
#                     "url": kwargs.get("url", ""),
#                     "header": kwargs.get("header", "")
#                 }

#         # ... генерация content_id, сохранение в PostgreSQL ...
#         content_id = self.generate_content_id(**kwargs)
        

#         # 3. ✅ ОБЯЗАТЕЛЬНО СОХРАНЯЕМ В POSTGRESQL
#         if self.postgres_processor:
#             saved_in_pg = self.postgres_processor.save_document(
#                 content_id=content_id,
#                 user_id=user_id,
#                 content_text=clean_text,
#                 content_hash=content_hash,
#                 url=kwargs.get("url", ""),
#                 header=kwargs.get("header", ""),
#                 document_id=document_id
#             )
#             if not saved_in_pg:
#                 raise RuntimeError("Не удалось сохранить документ в PostgreSQL")

#         # Чанкинг и эмбеддинги
#         chunk_tuples = semantic_chunk(clean_text, max_chunk_size=chunk_size, overlap=overlap)
#         chunks_texts = [c[0] for c in chunk_tuples]
#         embeddings = self.embedder.embed(chunks_texts, emb_type=emb_type)

#         # Присвоение кластеров (если есть)
#         cluster_labels = [None] * len(embeddings)
#         cluster_descriptions = {}
#         if self.postgres_processor:
#             centroids = self.postgres_processor.get_cluster_centroids(user_id)
#             if centroids:
#                 for i, vec in enumerate(embeddings):
#                     best_label = None
#                     best_sim = 0.3  # порог схожести
#                     for label, data in centroids.items():
#                         sim = cosine_similarity(vec, data["centroid"])
#                         if sim > best_sim:
#                             best_sim = sim
#                             best_label = label
#                     cluster_labels[i] = best_label
#                     if best_label:
#                         cluster_descriptions[best_label] = data["description"]

#         # Подготовка данных для Qdrant
#         chunks_for_qdrant = []
#         for i, ((chunk_text, start, end), vector) in enumerate(zip(chunk_tuples, embeddings)):
#             payload = {
#                 "dense_vector": vector,
#                 "sparse_vector": None,
#                 "content_id": content_id,
#                 "chunk_id": str(uuid.uuid4()),
#                 "chunk_order": i,
#                 "chunk_text": chunk_text,
#                 "chunk_start": start,
#                 "chunk_end": end,
#                 "user_id": user_id,
#                 "url": kwargs.get("url", ""),
#                 "header": kwargs.get("header", ""),
#                 "content_hash": content_hash,
#                 "cluster_label": cluster_labels[i],
#                 "cluster_description": cluster_descriptions.get(cluster_labels[i], "")
#             }
#             chunks_for_qdrant.append(payload)

#         point_ids = qdrant_manager.save_chunks(chunks_for_qdrant)

#         return {
#                 "content_id": content_id,
#                 "saved_chunks": len(point_ids),
#                 "status": "created",
#                 "user_id": kwargs.get("user_id", 0),
#                 "url": kwargs.get("url", ""),
#                 "header": kwargs.get("header", "")
#             }




from app.postgres_processor import PostgresProcessor
from app.embedder import Embedder
from typing import List, Dict, Any, Optional, Literal
from app.chunker import semantic_chunk
import uuid
import hashlib
from app.qdrant_manager import QdrantManager
from app.cluster_utils import cosine_similarity


class ContentProcessor:
    def __init__(self, embedder: Embedder, postgres_processor: Optional[PostgresProcessor] = None):
        self.embedder = embedder
        self.postgres_processor = postgres_processor

    def generate_content_id(self, **kwargs) -> int:
        """
        Генерирует уникальный числовой ID документа.
        Использует UUID для гарантии уникальности, затем преобразует в int.
        """
        unique_id = uuid.uuid4()
        content_id = int(unique_id.int % (10 ** 16))
        return content_id

    def process_and_save(
        self,
        text: str,
        qdrant_manager: QdrantManager,
        chunk_size: int = 2000,
        overlap: int = 200,
        emb_type: str = "passage",
        **kwargs
    ) -> Dict[str, Any]:
        clean_text = text.strip()
        user_id = kwargs.get("user_id", 0)
        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        print("=======>>>", user_id, content_hash)
        point_ids = []

        # Проверка дубликата
        if self.postgres_processor:
            existing_id = self.postgres_processor.get_content_id_by_hash(user_id, content_hash)
            if existing_id is not None:
                return {
                    "content_id": existing_id,
                    "saved_chunks": len(point_ids),
                    "status": "duplicates",
                    "user_id": kwargs.get("user_id", 0),
                    "url": kwargs.get("url", ""),
                    "header": kwargs.get("header", "")
                }

        # Генерация ID
        content_id = self.generate_content_id(**kwargs)
        header = kwargs.get("header", "")
        url = kwargs.get("url", "")
        # === ГЕНЕРАЦИЯ document_id ===
        document_id = hashlib.sha256(f"{user_id}_{content_hash}_{header}_{url}".encode()).hexdigest()[:16]

        # Сохраняем в PostgreSQL
        if self.postgres_processor:
            saved_in_pg = self.postgres_processor.save_document(
                content_id=content_id,
                user_id=user_id,
                content_text=clean_text,
                content_hash=content_hash,
                url=url,
                header=header,
                document_id=document_id  # ← ДОБАВЛЕНО
            )
            if not saved_in_pg:
                raise RuntimeError("Не удалось сохранить документ в PostgreSQL")

        # Чанкинг и эмбеддинги
        chunk_tuples = semantic_chunk(clean_text, max_chunk_size=chunk_size, overlap=overlap)
        chunks_texts = [c[0] for c in chunk_tuples]
        embeddings = self.embedder.embed(chunks_texts, emb_type=emb_type)

        # Присвоение кластеров (если есть)
        cluster_labels = [None] * len(embeddings)
        cluster_descriptions = {}
        if self.postgres_processor:
            centroids = self.postgres_processor.get_cluster_centroids(user_id)
            if centroids:
                for i, vec in enumerate(embeddings):
                    best_label = None
                    best_sim = 0.3
                    for label, data in centroids.items():
                        sim = cosine_similarity(vec, data["centroid"])
                        if sim > best_sim:
                            best_sim = sim
                            best_label = label
                    cluster_labels[i] = best_label
                    if best_label:
                        cluster_descriptions[best_label] = data["description"]

        # Подготовка данных для Qdrant
        chunks_for_qdrant = []
        for i, ((chunk_text, start, end), vector) in enumerate(zip(chunk_tuples, embeddings)):
            payload = {
                "dense_vector": vector,
                "sparse_vector": None,
                "content_id": content_id,
                "chunk_id": str(uuid.uuid4()),
                "chunk_order": i,
                "chunk_text": chunk_text,
                "chunk_start": start,
                "chunk_end": end,
                "user_id": user_id,
                "url": url,
                "header": header,
                "content_hash": content_hash,
                "cluster_label": cluster_labels[i],
                "cluster_description": cluster_descriptions.get(cluster_labels[i], ""),
                # === ДОБАВЛЕН document_id ===
                "document_id": document_id
            }
            chunks_for_qdrant.append(payload)

        point_ids = qdrant_manager.save_chunks(chunks_for_qdrant)

        return {
            "content_id": content_id,
            "document_id": document_id,  # ← добавлено в ответ
            "saved_chunks": len(point_ids),
            "status": "created",
            "user_id": user_id,
            "url": url,
            "header": header
        }