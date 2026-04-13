from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import traceback

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, User, GuestUsage
from app.services import get_rag_service
from app.api.auth import get_optional_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

GUEST_MAX_USES = 5


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


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host


async def _check_guest_limit(ip: str, db: AsyncSession) -> None:
    """게스트 사용 횟수 확인 및 증가. 한도 초과 시 429 반환."""
    result = await db.execute(select(GuestUsage).where(GuestUsage.ip == ip))
    record = result.scalar_one_or_none()

    if record is None:
        db.add(GuestUsage(ip=ip, count=1))
        await db.commit()
        return

    if record.count >= GUEST_MAX_USES:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "GUEST_LIMIT_EXCEEDED",
                "message": f"비회원은 {GUEST_MAX_USES}회까지 이용할 수 있어요. 계속 이용하려면 로그인해 주세요.",
                "used": record.count,
                "limit": GUEST_MAX_USES,
            },
        )

    record.count += 1
    await db.commit()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """연애 상담 채팅 엔드포인트"""
    if current_user is None:
        await _check_guest_limit(_get_client_ip(request), db)

    try:
        rag_service = get_rag_service()

        chat_history = None
        if body.history:
            chat_history = [
                {"role": msg.role, "content": msg.content}
                for msg in body.history
            ]

        result = rag_service.get_response(
            user_message=body.message,
            chat_history=chat_history,
        )

        return ChatResponse(
            response=result["response"],
            sources=[
                SourceInfo(content=s["content"], score=s["score"])
                for s in result["sources"]
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chat Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요.")


@router.post("/stream")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """SSE 스트리밍 채팅 엔드포인트"""
    if current_user is None:
        await _check_guest_limit(_get_client_ip(request), db)

    rag_service = get_rag_service()

    chat_history = None
    if body.history:
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in body.history
        ]

    return StreamingResponse(
        rag_service.stream_response(
            user_message=body.message,
            chat_history=chat_history,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}
