# FastAPI 보안 개선 작업 기록

RAG 기반 연애 상담 챗봇 백엔드를 개발하면서 적용한 보안 개선 사항을 정리합니다.

---

## 1. 채팅 엔드포인트 인증 적용

### 문제

`POST /api/chat/`, `POST /api/chat/stream` 엔드포인트가 인증 없이 누구나 호출 가능한 상태였습니다. 로그인 기능이 있어도 API를 직접 호출하면 우회가 가능했습니다.

### 해결

FastAPI의 `Depends`를 활용해 JWT 인증 의존성을 엔드포인트에 주입했습니다.

```python
# Before
@router.post("/")
async def chat(request: ChatRequest):
    ...

# After
@router.post("/")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    ...
```

`get_current_user`는 `Authorization: Bearer <token>` 헤더를 검증하고, 토큰이 없거나 유효하지 않으면 `401`을 반환합니다.

---

## 2. 게스트 사용 횟수 제한

### 문제

인증을 강제하면 서비스 체험 자체가 불가능합니다. 그렇다고 인증을 없애면 누구나 무제한으로 LLM API를 호출할 수 있습니다.

### 해결

비로그인 사용자(게스트)는 IP 기반으로 최대 5회까지만 허용하고, 초과 시 로그인을 유도합니다.

**DB 테이블 추가**

```python
class GuestUsage(Base):
    __tablename__ = "guest_usages"

    id = Column(Integer, primary_key=True)
    ip = Column(String(64), unique=True, nullable=False, index=True)
    count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, ...)
```

**제한 로직**

```python
GUEST_MAX_USES = 5

async def _check_guest_limit(ip: str, db: AsyncSession) -> None:
    record = await db.execute(select(GuestUsage).where(GuestUsage.ip == ip))
    ...
    if record.count >= GUEST_MAX_USES:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "GUEST_LIMIT_EXCEEDED",
                "message": "비회원은 5회까지 이용할 수 있어요. 계속 이용하려면 로그인해 주세요.",
            },
        )
    record.count += 1
```

`get_optional_user` 의존성으로 토큰 유무를 판별하고, 게스트일 때만 횟수 검사를 수행합니다.

| 상태 | 결과 |
|------|------|
| 로그인 사용자 | 제한 없음 |
| 게스트 1~5회 | 정상 응답 |
| 게스트 6회 이상 | `429 Too Many Requests` |

---

## 3. 내부 에러 메시지 노출 차단

### 문제

예외 발생 시 `str(e)`를 그대로 응답에 포함했습니다. 스택 트레이스나 DB 쿼리, 파일 경로 같은 내부 정보가 클라이언트에 노출될 수 있었습니다.

```python
# Before — 내부 예외 메시지가 그대로 노출
raise HTTPException(status_code=500, detail=str(e))
```

### 해결

내부 에러는 서버 로그에만 기록하고, 클라이언트에는 일반화된 메시지를 반환합니다.

```python
# After
except Exception as e:
    print(f"Chat Error: {e}")
    traceback.print_exc()  # 서버 로그에만 기록
    raise HTTPException(
        status_code=500,
        detail="일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요."
    )
```

---

## 4. 비밀번호 복잡도 검증

### 문제

회원가입 시 `"1234"` 같은 단순 비밀번호도 허용됐습니다.

### 해결

Pydantic의 `field_validator`로 회원가입 요청 시 비밀번호를 즉시 검증합니다.

```python
class RegisterRequest(BaseModel):
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
```

**적용 조건**

| 조건 | 기준 |
|------|------|
| 최소 길이 | 8자 이상 |
| 영문자 | 최소 1자 |
| 숫자 | 최소 1자 |
| 특수문자 | 최소 1자 |

조건 미충족 시 어떤 조건이 빠졌는지 구체적으로 응답합니다.

```json
{
  "detail": [
    { "msg": "비밀번호 조건을 확인해 주세요: 8자 이상, 특수문자 포함" }
  ]
}
```

---

## 5. JWT 만료 시간 조정 및 Secret Key 외부화

### 문제 1 — 만료 시간

JWT 토큰 만료 시간이 7일로 설정되어 있었습니다. 토큰이 탈취되면 7일간 유효한 상태가 지속됩니다.

```python
# Before
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7일

# After
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간
```

연애 상담 챗봇은 결제나 민감한 개인정보를 다루지 않아 UX를 고려해 24시간으로 설정했습니다. 보안 민감도가 높은 서비스라면 1시간 Access Token + Refresh Token 구조가 권장됩니다.

### 문제 2 — Secret Key 하드코딩

JWT 서명에 사용하는 Secret Key가 코드에 직접 포함되어 있었습니다.

```python
# Before — 코드에 하드코딩
SECRET_KEY = "love-counselor-secret-key-change-in-production"
```

### 해결

환경변수로 분리하고 `config.py`의 `Settings`에서 관리합니다.

```python
# config.py
class Settings(BaseSettings):
    jwt_secret_key: str  # 필수값 — 없으면 서버 시작 실패

# auth_service.py
def create_access_token(user_id: int, username: str) -> str:
    secret_key = get_settings().jwt_secret_key
    ...
```

`.env.example`에 생성 방법을 명시했습니다.

```bash
# python -c "import secrets; print(secrets.token_hex(32))" 로 생성
JWT_SECRET_KEY=your_jwt_secret_key_here
```

---

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `app/api/chat.py` | 인증 적용, 게스트 제한, 에러 메시지 일반화 |
| `app/api/auth.py` | 비밀번호 복잡도 검증 추가 |
| `app/database.py` | `GuestUsage` 테이블 추가 |
| `app/services/auth_service.py` | JWT 만료 시간 단축, Secret Key 외부화 |
| `app/config.py` | `jwt_secret_key` 설정 추가 |
| `.env.example` | `JWT_SECRET_KEY` 항목 추가 |
