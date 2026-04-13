import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, AsyncGenerator

from app.services.qdrant_service import get_qdrant_service
from app.services.huggingface_service import get_huggingface_service

_executor = ThreadPoolExecutor(max_workers=4)


SCORE_THRESHOLD = 0.45   # 이 점수 미만은 참고자료로 쓰지 않음
MAX_CONTEXT_DOCS = 3     # LLM에 넘기는 최대 참고자료 수


class RAGService:
    def __init__(self):
        self.qdrant = get_qdrant_service()
        self.llm = get_huggingface_service()

    def _filter_docs(self, docs: List[Dict]) -> List[Dict]:
        """score threshold 필터 + 중복 내용 제거"""
        seen, filtered = set(), []
        for doc in docs:
            if doc["score"] < SCORE_THRESHOLD:
                continue
            content = doc["content"][:100]   # 앞 100자 기준으로 중복 판단
            if content in seen:
                continue
            seen.add(content)
            filtered.append(doc)
            if len(filtered) >= MAX_CONTEXT_DOCS:
                break
        return filtered

    def get_response(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]] = None,
        top_k: int = 8
    ) -> Dict[str, any]:
        candidates = self.qdrant.search(user_message, top_k=top_k)
        relevant_docs = self._filter_docs(candidates)
        response = self.llm.generate_response(
            user_message=user_message,
            context_docs=relevant_docs,
            chat_history=chat_history
        )
        return {
            "response": response,
            "sources": [
                {
                    "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                    "score": doc["score"]
                }
                for doc in relevant_docs
            ]
        }

    async def stream_response(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]] = None,
        top_k: int = 8
    ) -> AsyncGenerator[str, None]:
        """HuggingFace sync 스트리밍을 async SSE로 변환"""
        candidates = self.qdrant.search(user_message, top_k=top_k)
        relevant_docs = self._filter_docs(candidates)

        sources = [
            {
                "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                "score": doc["score"]
            }
            for doc in relevant_docs
        ]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"

        # sync 제너레이터 → async 큐 브리징
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def run_sync():
            try:
                for token in self.llm.stream_response(user_message, relevant_docs, chat_history):
                    loop.call_soon_threadsafe(queue.put_nowait, token)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, Exception(str(e)))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        loop.run_in_executor(_executor, run_sync)

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield f"data: {json.dumps({'type': 'token', 'content': item}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.04)  # 토큰 간 딜레이 (40ms)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"


_rag_service = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
