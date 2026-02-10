# app/services/search_service.py
from typing import List, Optional
from app.reranker import Reranker
from app.qdrant_manager import QdrantManager
from app.postgres_processor import PostgresProcessor
from app.embedder import Embedder
from qdrant_client.models import Filter, FieldCondition, MatchValue

class SearchService:
    def __init__(self, embedder: Embedder, reranker: Reranker, 
                 qdrant_manager: QdrantManager, postgres_processor: PostgresProcessor):
        self.embedder = embedder
        self.reranker = reranker
        self.qdrant_manager = qdrant_manager
        self.postgres_processor = postgres_processor

    def search(self, user_id: int, query: str, cluster_label: Optional[str] = None, limit: int = 5) -> List[dict]:
        """Выполняет семантический поиск по документам пользователя"""
        query_embedding = self.embedder.embed([query], "query")[0]
        
        must_conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        if cluster_label is not None:
            must_conditions.append(FieldCondition(key="cluster_label", match=MatchValue(value=cluster_label)))
        search_filter = Filter(must=must_conditions)
        
        all_chunks = self.qdrant_manager.client.query_points(
            collection_name="content_chunks",
            query=query_embedding,
            using="dense",
            query_filter=search_filter,
            limit=1000
        ).points
        
        if not all_chunks:
            return []
        
        chunk_texts = [chunk.payload["chunk_text"] for chunk in all_chunks]
        reranked_pairs = self.reranker.rerank(query, chunk_texts, top_k=None)
        rerank_scores = [float(score) for score, _ in reranked_pairs]
        
        RERANK_THRESHOLD = 0.15
        relevant_chunks = []
        relevant_scores = []
        for i, chunk in enumerate(all_chunks):
            score = rerank_scores[i]
            if score > RERANK_THRESHOLD:
                relevant_chunks.append(chunk)
                relevant_scores.append(score)
        
        if not relevant_chunks:
            return []
        
        relevant_content_ids = list(set(int(chunk.payload["content_id"]) for chunk in relevant_chunks))
        documents = self.postgres_processor.get_documents_by_content_ids(relevant_content_ids, user_id)
        
        content_id_to_best_score = {}
        for i, chunk in enumerate(relevant_chunks):
            content_id = int(chunk.payload["content_id"])
            current_score = relevant_scores[i]
            if content_id not in content_id_to_best_score or current_score > content_id_to_best_score[content_id]:
                content_id_to_best_score[content_id] = current_score
        
        results_with_score = []
        for doc in documents:
            doc["rerank_score"] = content_id_to_best_score.get(doc["content_id"], 0.0)
            results_with_score.append(doc)
        
        results_with_score.sort(key=lambda x: x["rerank_score"], reverse=True)
        return results_with_score[:limit]