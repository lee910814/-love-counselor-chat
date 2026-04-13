from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import uuid

from app.config import get_settings


class QdrantService:
    def __init__(self):
        settings = get_settings()
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )
        # 모델 이름에서 안전한 식별자 추출 (예: sentence-transformers/ko-sroberta -> ko_sroberta)
        model_name_sanitized = settings.embedding_model.split('/')[-1].replace('-', '_')
        self.collection_name = f"{settings.qdrant_collection_name}_{model_name_sanitized}"
        
        self.model = SentenceTransformer(settings.embedding_model)
        self.vector_size = self.model.get_sentence_embedding_dimension()

        self._ensure_collection()

    def _ensure_collection(self):
        """컬렉션이 없으면 생성"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )

    def embed_text(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환"""
        return self.model.encode(text).tolist()

    def add_documents(self, documents: List[Dict[str, Any]]):
        """문서들을 벡터 DB에 추가

        Args:
            documents: [{"content": str, "metadata": dict}, ...]
        """
        points = []
        for doc in documents:
            vector = self.embed_text(doc["content"])
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "content": doc["content"],
                    **doc.get("metadata", {})
                }
            )
            points.append(point)

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """유사 문서 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수

        Returns:
            유사 문서 리스트
        """
        query_vector = self.embed_text(query)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k
        )

        return [
            {
                "content": hit.payload.get("content", ""),
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items() if k != "content"}
            }
            for hit in results
        ]


# 싱글톤 인스턴스
_qdrant_service = None


def get_qdrant_service() -> QdrantService:
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service
