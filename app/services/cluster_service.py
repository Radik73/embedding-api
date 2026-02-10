# app/services/cluster_service.py
from typing import Dict
from app.qdrant_manager import QdrantManager
from app.postgres_processor import PostgresProcessor
from app.cluster_utils import cluster_chunks_umap_hdbscan
from qdrant_client.models import Filter, FieldCondition, MatchValue

class ClusterService:
    def __init__(self, qdrant_manager: QdrantManager, postgres_processor: PostgresProcessor):
        self.qdrant_manager = qdrant_manager
        self.postgres_processor = postgres_processor

    def clusterize_user(self, user_id: int) -> Dict[str, int]:
        """Кластеризует чанки пользователя и сохраняет результаты"""
        scroll_filter = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
        points, _ = self.qdrant_manager.client.scroll(
            collection_name="content_chunks",
            scroll_filter=scroll_filter,
            with_vectors=True,
            limit=10000
        )

        if not points:
            return {"status": "no_chunks"}

        vectors = [p.vector["dense"] for p in points]
        point_ids = [p.id for p in points]
        labels, centroids_dict = cluster_chunks_umap_hdbscan(vectors)

        # TODO: подключить LLM-генерацию описаний
        descriptions = {label: f"Кластер {label}" for label in centroids_dict.keys() if label != -1}

        centroid_data = {
            str(label): {"centroid": centroid, "description": descriptions.get(label, f"Кластер {label}")}
            for label, centroid in centroids_dict.items()
        }
        self.postgres_processor.save_cluster_centroids(user_id, centroid_data)

        for i, label in enumerate(labels):
            if label == -1:
                continue
            self.qdrant_manager.client.set_payload(
                collection_name="content_chunks",
                payload={
                    "cluster_label": str(label),
                    "cluster_description": descriptions.get(label, f"Кластер {label}")
                },
                points=[point_ids[i]]
            )

        return {"status": "success", "clusters_found": len(centroids_dict)}