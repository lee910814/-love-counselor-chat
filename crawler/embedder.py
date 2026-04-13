from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import uuid
import os
from dotenv import load_dotenv

from crawlers.base import CrawledItem

load_dotenv()


class Embedder:
    """임베딩 생성 및 Qdrant 저장"""

    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        base_collection_name = os.getenv("QDRANT_COLLECTION_NAME", "love_counselor")
        self.model_name = os.getenv(
            "EMBEDDING_MODEL",
            "jhgan/ko-sroberta-multitask"
        )
        
        # 모델 이름에서 안전한 식별자 추출 (백엔드와 동일한 로직)
        model_name_sanitized = self.model_name.split('/')[-1].replace('-', '_')
        self.collection_name = f"{base_collection_name}_{model_name_sanitized}"

        print(f"임베딩 모델 로드 중: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.vector_size = self.model.get_sentence_embedding_dimension()

        print(f"Qdrant 연결: {self.qdrant_host}:{self.qdrant_port}")
        self.client = QdrantClient(
            host=self.qdrant_host,
            port=self.qdrant_port
        )

        self._ensure_collection()

    def _ensure_collection(self):
        """컬렉션 생성 확인"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            print(f"컬렉션 생성: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
        else:
            print(f"컬렉션 존재: {self.collection_name}")

    def embed_and_store(
        self,
        items: List[CrawledItem],
        batch_size: int = 100
    ):
        """크롤링된 아이템을 임베딩하여 Qdrant에 저장

        Args:
            items: 크롤링된 아이템 리스트
            batch_size: 배치 크기
        """
        print(f"총 {len(items)}개 아이템 임베딩 및 저장 시작")

        for i in tqdm(range(0, len(items), batch_size), desc="Embedding"):
            batch = items[i:i + batch_size]

            # 임베딩 생성
            texts = [item.content for item in batch]
            embeddings = self.model.encode(texts, show_progress_bar=False)

            # Qdrant 포인트 생성
            points = []
            for item, embedding in zip(batch, embeddings):
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding.tolist(),
                    payload={
                        "content": item.content,
                        "source": item.source,
                        "url": item.url,
                        **(item.metadata or {})
                    }
                )
                points.append(point)

            # Qdrant에 저장
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

        print(f"저장 완료: {len(items)}개")

    def get_collection_info(self):
        """컬렉션 정보 조회"""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count
        }
