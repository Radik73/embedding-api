# app/services/document_service.py
from app.content_processor import ContentProcessor
from app.qdrant_manager import QdrantManager

class DocumentService:
    def __init__(self, content_processor: ContentProcessor, qdrant_manager: QdrantManager):
        self.content_processor = content_processor
        self.qdrant_manager = qdrant_manager

    def save_document(self, text: str, user_id: int, chunk_size: int = 1500, 
                     overlap: int = 40, url: str = "", header: str = ""):
        """Сохраняет документ и его чанки"""
        return self.content_processor.process_and_save(
            text=text,
            qdrant_manager=self.qdrant_manager,
            chunk_size=chunk_size,
            overlap=overlap,
            user_id=user_id,
            url=url,
            header=header
        )