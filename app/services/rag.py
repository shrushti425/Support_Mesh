import logging
import asyncio
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sentence_transformers import SentenceTransformer
from app.models import KnowledgeBase

logger = logging.getLogger("supportmesh.rag")

class RAGService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            logger.info(f"Loading sentence-transformer model: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully.")

    async def get_embedding(self, text: str) -> List[float]:
        try:
            if self._model is None:
                await asyncio.to_thread(self._load_model)
            # Run model execution in a background thread to avoid blocking the event loop
            embedding = await asyncio.to_thread(self._model.encode, text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def search_knowledge_base(
        self, db: AsyncSession, query: str, limit: int = 3
    ) -> List[KnowledgeBase]:
        try:
            # Generate embedding for the ticket text
            query_vector = await self.get_embedding(query)
            
            # Query knowledge base using cosine distance
            stmt = (
                select(KnowledgeBase)
                .order_by(KnowledgeBase.embedding.cosine_distance(query_vector))
                .limit(limit)
            )
            result = await db.execute(stmt)
            articles = result.scalars().all()
            return list(articles)
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

# Singleton instance
rag_service = RAGService()
