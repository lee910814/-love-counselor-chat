from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

from app.database import get_db, ChatSession, ChatMessage, User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# --- Schemas ---

class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class SessionDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut]


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "새 대화"


class SaveMessagesRequest(BaseModel):
    session_id: int
    messages: List[dict]   # [{"role": "user"|"assistant", "content": str}]


# --- Endpoints ---

@router.post("/", response_model=SessionOut)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ChatSession(title=body.title, user_id=current_user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/", response_model=List[SessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/{session_id}", response_model=SessionDetailOut)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없어요")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    return SessionDetailOut(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=messages,
    )


@router.post("/{session_id}/messages")
async def save_messages(
    session_id: int,
    body: SaveMessagesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없어요")

    for msg in body.messages:
        db.add(ChatMessage(session_id=session_id, role=msg["role"], content=msg["content"]))

    if session.title == "새 대화":
        user_msgs = [m for m in body.messages if m["role"] == "user"]
        if user_msgs:
            await db.execute(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(title=user_msgs[0]["content"][:40])
            )

    await db.commit()
    return {"ok": True}


@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없어요")

    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()
    return {"ok": True}
