# app/main.py
# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Tuple, Optional

# Импорты компонентов
from .embedder import Embedder
from app.settings.models import *
from app.settings.db_credentials import *
from .chunker import semantic_chunk
from app.content_processor import ContentProcessor
from app.qdrant_manager import QdrantManager
from app.postgres_processor import PostgresProcessor
from app.reranker import Reranker
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Импорты сервисов
from app.services.document_service import DocumentService
from app.services.search_service import SearchService
from app.services.cluster_service import ClusterService

app = FastAPI(
    title="Embedding API",
    description="API для получения семантических векторов (русский + 100 языков)",
    version="1.0"
)

# === Инициализация глобальных компонентов ===
embedder = Embedder()
reranker = Reranker()
qdrant_manager = QdrantManager(host=qdrant_host, port=qdrant_port)
postgres_processor = PostgresProcessor()
content_processor = ContentProcessor(embedder, postgres_processor)

# === Инициализация сервисов ===
document_service = DocumentService(content_processor, qdrant_manager)
search_service = SearchService(embedder, reranker, qdrant_manager, postgres_processor)
cluster_service = ClusterService(qdrant_manager, postgres_processor)


# === Модели запросов/ответов ===
class EmbedRequest(BaseModel):
    texts: List[str]
    type: Literal["query", "passage"] = "query"

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dim: int
    type: str

class ChunkEmbedRequest(BaseModel):
    text: str
    chunk_size: int = 1500
    overlap: int = 40
    emb_type: Literal["query", "passage"] = "passage"

class ChunkEmbedResponse(BaseModel):
    chunks: List[str]
    embeddings: List[List[float]]
    positions: List[Tuple[int, int]]
    dim: int

class ProcessRequest(BaseModel):
    text: str
    chunk_size: int = 2000
    overlap: int = 200
    emb_type: Literal["query", "passage"] = "passage"
    url: str = ""
    header: str = ""
    user_id: int = 0

class SaveContentRequest(BaseModel):
    text: str
    chunk_size: int = 1500
    overlap: int = 40
    user_id: int
    url: str = ""
    header: str = ""

class SearchRequest(BaseModel):
    user_id: int
    query: str
    cluster_label: Optional[str] = None
    limit: int = 5


# === Эндпоинты ===
@app.get("/health")
async def health():
    return {"status": "ok", "model": transformer_model_name}


@app.post("/embed", response_model=EmbedResponse)
async def embed_endpoint(req: EmbedRequest):
    if not req.texts:
        raise HTTPException(status_code=400, detail="Список texts не может быть пустым")
    try:
        embeddings = embedder.embed(req.texts, req.type)
        return EmbedResponse(
            embeddings=embeddings,
            dim=len(embeddings[0]) if embeddings else 0,
            type=req.type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации эмбеддингов: {str(e)}")


@app.post("/chunk-embed", response_model=ChunkEmbedResponse)
async def chunk_embed_endpoint(req: ChunkEmbedRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Текст не может быть пустым")
    if req.chunk_size <= 0:
        raise HTTPException(status_code=400, detail="chunk_size должен быть > 0")
    if req.overlap < 0:
        raise HTTPException(status_code=400, detail="overlap не может быть отрицательным")
    if req.overlap >= req.chunk_size:
        req.overlap = req.chunk_size // 4
    
    try:
        chunk_tuples = semantic_chunk(
            req.text,
            max_chunk_size=req.chunk_size,
            overlap=req.overlap
        )
        chunks = [c[0] for c in chunk_tuples]
        positions = [(c[1], c[2]) for c in chunk_tuples]

        if not chunks:
            return ChunkEmbedResponse(chunks=[], embeddings=[], positions=[], dim=0)

        MAX_CHUNKS = 100
        if len(chunks) > MAX_CHUNKS:
            chunks = chunks[:MAX_CHUNKS]
            positions = positions[:MAX_CHUNKS]
        
        embeddings = embedder.embed(chunks, req.emb_type)
        return ChunkEmbedResponse(
            chunks=chunks,
            embeddings=embeddings,
            positions=positions,
            dim=len(embeddings[0]) if embeddings else 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")


@app.post("/process")
async def process_endpoint(req: ProcessRequest):
    if not req.text.strip():
        raise HTTPException(400, "text не может быть пустым")
    try:
        result = content_processor.process(
            text=req.text,
            chunk_size=req.chunk_size,
            overlap=req.overlap,
            emb_type=req.emb_type,
            url=req.url,
            header=req.header,
            user_id=req.user_id
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Ошибка обработки: {e}")


@app.post("/save-content")
async def save_content(req: SaveContentRequest):
    try:
        result = document_service.save_document(
            text=req.text,
            user_id=req.user_id,
            chunk_size=req.chunk_size,
            overlap=req.overlap,
            url=req.url,
            header=req.header
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(500, f"Ошибка сохранения: {e}")


@app.post("/clusterize")
async def clusterize_user_content(user_id: int):
    try:
        result = cluster_service.clusterize_user(user_id)
        return result
    except Exception as e:
        raise HTTPException(500, f"Ошибка кластеризации: {e}")


@app.get("/clusters")
async def get_user_clusters(user_id: int):
    scroll_filter = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
    points, _ = qdrant_manager.client.scroll(
        collection_name="content_chunks",
        scroll_filter=scroll_filter,
        limit=1000
    )
    
    clusters = {}
    for p in points:
        label = p.payload.get("cluster_label")
        desc = p.payload.get("cluster_description")
        if label is not None and desc:
            clusters[str(label)] = desc
    
    return {"clusters": [{"label": k, "description": v} for k, v in clusters.items()]}


@app.post("/search")
async def search_chunks(req: SearchRequest):
    try:
        results = search_service.search(
            user_id=req.user_id,
            query=req.query,
            cluster_label=req.cluster_label,
            limit=req.limit
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(500, f"Ошибка поиска: {e}")