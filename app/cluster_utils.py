# app/cluster_utils.py
import numpy as np
import umap
import hdbscan
from typing import List, Tuple, Dict

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Вычисляет косинусное сходство между двумя векторами"""
    a = np.array(a)
    b = np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def cluster_chunks_umap_hdbscan(vectors: List[List[float]]) -> Tuple[List[int], Dict[int, List[float]]]:
    n_points = len(vectors)
    
    # Случай 0: нет данных
    if n_points == 0:
        return [], {}
    
    # Случай 1: один чанк → один кластер
    if n_points == 1:
        return [0], {0: vectors[0]}
    
    # Случай 2: два чанка → объединяем если похожи, иначе разделяем
    if n_points == 2:
        sim = cosine_similarity(vectors[0], vectors[1])
        if sim > 0.5:  # Порог схожести
            return [0, 0], {0: np.mean(vectors, axis=0).tolist()}
        else:
            return [0, 1], {0: vectors[0], 1: vectors[1]}
    
    # Случай 3: 3-4 чанка → простая кластеризация без UMAP
    if n_points < 5:
        # Группируем по схожести
        labels = [0] * n_points
        centroids = {}
        current_label = 0
        
        for i in range(n_points):
            if labels[i] != 0:  # Уже назначено
                continue
            labels[i] = current_label
            similar_indices = [i]
            
            # Ищем похожие чанки
            for j in range(i + 1, n_points):
                if labels[j] == 0 and cosine_similarity(vectors[i], vectors[j]) > 0.5:
                    labels[j] = current_label
                    similar_indices.append(j)
            
            # Вычисляем центроид
            cluster_vecs = [vectors[idx] for idx in similar_indices]
            centroids[current_label] = np.mean(cluster_vecs, axis=0).tolist()
            current_label += 1
        
        return labels, centroids

    # Случай 4: 5+ чанков → UMAP + HDBSCAN
    try:
        # Безопасные параметры для UMAP
        n_neighbors = min(15, max(2, n_points // 2))
        n_components = min(10, n_points - 1)
        
        reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            n_components=n_components,
            random_state=42,
            metric='cosine'  # Лучше для текстовых эмбеддингов
        )
        embeddings_2d = reducer.fit_transform(vectors)
        
        # HDBSCAN с адаптивными параметрами
        min_cluster_size = min(2, max(2, n_points // 3))
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=1,
            metric='euclidean',
            core_dist_n_jobs=1
        )
        labels = clusterer.fit_predict(embeddings_2d)
        
        # Обработка результатов
        centroids = {}
        unique_labels = set(labels)
        
        # Если все точки - шум (-1), группируем по схожести
        if unique_labels == {-1}:
            return _fallback_similarity_clustering(vectors)
        
        # Собираем центроиды для не-шумных кластеров
        for label in unique_labels:
            if label == -1:
                continue
            cluster_indices = [i for i, l in enumerate(labels) if l == label]
            cluster_vecs = [vectors[i] for i in cluster_indices]
            centroids[label] = np.mean(cluster_vecs, axis=0).tolist()
        
        # Обработка шумовых точек (-1)
        noise_indices = [i for i, l in enumerate(labels) if l == -1]
        if noise_indices:
            # Каждую шумовую точку делаем отдельным кластером
            next_label = max(centroids.keys(), default=-1) + 1
            for idx in noise_indices:
                labels[idx] = next_label
                centroids[next_label] = vectors[idx]
                next_label += 1
        
        return labels, centroids
        
    except Exception as e:
        print(f"⚠️ UMAP/HDBSCAN failed ({e}), using similarity fallback")
        return _fallback_similarity_clustering(vectors)

def _fallback_similarity_clustering(vectors: List[List[float]]) -> Tuple[List[int], Dict[int, List[float]]]:
    """Резервный метод: кластеризация по косинусному сходству"""
    n_points = len(vectors)
    if n_points == 0:
        return [], {}
    if n_points == 1:
        return [0], {0: vectors[0]}
    
    labels = [-1] * n_points
    centroids = {}
    current_label = 0
    
    for i in range(n_points):
        if labels[i] != -1:
            continue
            
        labels[i] = current_label
        cluster_vecs = [vectors[i]]
        
        # Находим все похожие чанки
        for j in range(i + 1, n_points):
            if labels[j] == -1 and cosine_similarity(vectors[i], vectors[j]) > 0.5:
                labels[j] = current_label
                cluster_vecs.append(vectors[j])
        
        centroids[current_label] = np.mean(cluster_vecs, axis=0).tolist()
        current_label += 1
    
    return labels, centroids