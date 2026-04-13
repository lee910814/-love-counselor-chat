from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import traceback

from app.services import get_rag_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = None


class SourceInfo(BaseModel):
    content: str
    score: float


class ChatResponse(BaseModel):
    response: str
    sources: List[SourceInfo]


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """연애 상담 채팅 엔드포인트"""
    try:
        rag_service = get_rag_service()

        # 대화 기록 변환
        chat_history = None
        if request.history:
            chat_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.history
            ]

        result = rag_service.get_response(
            user_message=request.message,
            chat_history=chat_history
        )

        return ChatResponse(
            response=result["response"],
            sources=[
                SourceInfo(content=s["content"], score=s["score"])
                for s in result["sources"]
            ]
        )
    except Exception as e:
        print(f"Chat Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """SSE 스트리밍 채팅 엔드포인트"""
    rag_service = get_rag_service()

    chat_history = None
    if request.history:
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.history
        ]

    return StreamingResponse(
        rag_service.stream_response(
            user_message=request.message,
            chat_history=chat_history
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}
