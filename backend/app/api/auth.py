import re
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

from app.database import get_db, User, RefreshToken
from app.services.auth_service import (
    hash_password, verify_password,
    create_access_token, decode_token,
    generate_refresh_token, hash_refresh_token, get_refresh_expiry,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

REFRESH_COOKIE = "refresh_token"


# --- Schemas ---

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        errors = []
        if len(v) < 8:
            errors.append("8자 이상")
        if not re.search(r"[A-Za-z]", v):
            errors.append("영문자 포함")
        if not re.search(r"\d", v):
            errors.append("숫자 포함")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            errors.append("특수문자 포함")
        if errors:
            raise ValueError(f"비밀번호 조건을 확인해 주세요: {', '.join(errors)}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str


# --- Helpers ---

def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=False,       # 프로덕션에서는 True
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/auth")


async def _create_refresh_token_record(user_id: int, db: AsyncSession) -> str:
    """DB에 리프레시 토큰 저장 후 plain 토큰 반환."""
    plain, hashed = generate_refresh_token()
    rt = RefreshToken(user_id=user_id, token_hash=hashed, expires_at=get_refresh_expiry())
    db.add(rt)
    await db.commit()
    return plain


# --- Auth Dependency ---

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요해요")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰이에요")

    user = await db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없어요")

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    return await db.get(User, int(payload["sub"]))


# --- Endpoints ---

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    dup = await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일 또는 아이디에요")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    plain = await _create_refresh_token_record(user.id, db)
    _set_refresh_cookie(response, plain)

    token = create_access_token(user.id, user.username)
    return TokenResponse(access_token=token, user_id=user.id, username=user.username)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸어요")

    plain = await _create_refresh_token_record(user.id, db)
    _set_refresh_cookie(response, plain)

    token = create_access_token(user.id, user.username)
    return TokenResponse(access_token=token, user_id=user.id, username=user.username)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="리프레시 토큰이 없어요")

    token_hash = hash_refresh_token(refresh_token)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > now,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰이에요")

    user = await db.get(User, rt.user_id)
    if not user or not user.is_active:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없어요")

    # 토큰 로테이션: 기존 폐기 → 새 발급
    rt.revoked = True
    plain, hashed = generate_refresh_token()
    new_rt = RefreshToken(user_id=user.id, token_hash=hashed, expires_at=get_refresh_expiry())
    db.add(new_rt)
    await db.commit()

    _set_refresh_cookie(response, plain)
    token = create_access_token(user.id, user.username)
    return TokenResponse(access_token=token, user_id=user.id, username=user.username)


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE),
):
    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        rt = result.scalar_one_or_none()
        if rt:
            rt.revoked = True
            await db.commit()

    _clear_refresh_cookie(response)
    return {"message": "로그아웃 되었어요"}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
