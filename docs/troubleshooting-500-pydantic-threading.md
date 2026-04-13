# [트러블슈팅] 500 Internal Server Error — Pydantic v2 호환성 & 스레딩 모델

> 작성일: 2026-04-13  
> 프로젝트: RAG 기반 연애 상담 챗봇  
> 스택: FastAPI · Pydantic v2 · SQLAlchemy 2.0 · aiosqlite · uvicorn

---

## 문제 상황

`/api/sessions/` 엔드포인트를 처음 호출했을 때 500 에러가 반환됐다.

```
api.ts:104  GET http://localhost:5174/api/sessions/ 500 (Internal Server Error)
AxiosError: Request failed with status code 500
    at settle (settle.js:20:7)
    at XMLHttpRequest.onloadend (xhr.js:62:9)
```

코드 로직 자체는 문제가 없었고, 직접 Python으로 테스트하면 정상 동작했다.

---

## 원인 분석: Pydantic v2 호환성 문제

### 문제 코드

```python
# Pydantic v1 스타일 (구버전 방식)
class SessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # ← v1 방식
```

### 왜 문제가 되나?

이 프로젝트는 **Pydantic v2.5.3** 을 사용하고 있다.  
Pydantic v2에서 `class Config`는 **deprecated** 되었고, 내부적으로 v1 호환 레이어를 통해 처리된다.

SQLAlchemy ORM 객체를 Pydantic 모델로 직렬화할 때 (`from_attributes`),  
v1 호환 레이어에서 SQLite의 **naive datetime** (timezone 없음) 처리 방식이 충돌을 일으킨다.

```
SQLite datetime → datetime.datetime(2026, 4, 13, 9, 37, ...) # timezone 없음
         ↓
Pydantic v2 class Config 레이어에서 직렬화 시도
         ↓
ValidationError → FastAPI가 500으로 반환
```

### 해결 코드

```python
# Pydantic v2 네이티브 방식
from pydantic import BaseModel, ConfigDict

class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ← v2 방식

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
```

`model_config = ConfigDict(from_attributes=True)` 는 Pydantic v2의 공식 방식이다.  
ORM 객체를 직접 Pydantic 모델로 변환할 수 있게 해준다.

---

## 이 프로젝트는 단일 스레드인가, 멀티 스레드인가?

500 에러와 함께 스택 트레이스를 보면 `retryer.ts`, `queryObserver.ts` 같은 React Query 레이어가 보인다.  
이는 단순한 fetch가 아니라 React Query가 관리하는 비동기 요청임을 알 수 있다.

이 프로젝트의 스레딩 구조를 레이어별로 정리한다.

---

### 프론트엔드 (React + React Query)

**단일 스레드 (JavaScript)**

JavaScript는 싱글 스레드 언어다. React Query는 내부적으로 이벤트 루프(Event Loop)를 활용해  
`fetch`, `axios` 같은 비동기 I/O를 처리한다. 동시에 여러 요청이 가능하지만 실행 자체는 하나의 스레드에서 순차적으로 이루어진다.

```
[JS 메인 스레드]
    ↓
React Query → useQuery → GET /api/sessions/
    ↓
fetch (비동기) → 이벤트 루프에 위임
    ↓
응답 도착 → 콜백 실행
```

---

### 백엔드 (FastAPI + uvicorn)

**단일 스레드 기반 비동기 (asyncio)**

uvicorn은 기본적으로 **단일 프로세스, 단일 이벤트 루프**로 실행된다.  
멀티스레드가 아니라 `async/await` 기반의 **코루틴(coroutine)** 으로 동시성을 처리한다.

```python
# FastAPI 라우트 — async def 이므로 이벤트 루프에서 실행
@router.get("/")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(...)  # await → 다른 요청 처리 가능
    return result.scalars().all()
```

요청 A가 DB 응답을 기다리는 동안, 이벤트 루프는 요청 B를 처리한다.  
스레드를 추가로 만들지 않고도 수백 개의 동시 요청을 처리할 수 있다.

---

### SQLite (aiosqlite)

**내부적으로 스레드 풀 사용**

SQLite 자체는 동기(blocking) 라이브러리다.  
`aiosqlite`는 SQLite 호출을 **별도 스레드(ThreadPoolExecutor)** 에서 실행하고,  
결과를 asyncio 이벤트 루프로 돌려주는 브리지 역할을 한다.

```
[asyncio 이벤트 루프]
    │  await db.execute(...)
    ↓
[aiosqlite]
    │  run_in_executor
    ↓
[ThreadPoolExecutor 워커 스레드]
    │  sqlite3 (동기 I/O)
    ↓
[결과 반환 → asyncio 이벤트 루프]
```

---

### 전체 구조 요약

```
브라우저 (JS 단일 스레드)
  └─ React Query (비동기 fetch)
       │
       ▼
Vite 프록시 (Node.js 단일 스레드 + 이벤트 루프)
       │
       ▼
uvicorn + FastAPI (asyncio 단일 이벤트 루프)
  ├─ 라우트 처리: async/await 코루틴
  └─ DB 접근: aiosqlite → ThreadPoolExecutor (내부 스레드)
       │
       ▼
SQLite (파일 기반 DB)
```

| 레이어 | 스레딩 방식 | 동시성 처리 |
|--------|------------|------------|
| 브라우저 (React) | 단일 스레드 | 이벤트 루프 (JS) |
| Vite | 단일 스레드 | 이벤트 루프 (Node.js) |
| FastAPI + uvicorn | 단일 스레드 | asyncio 코루틴 |
| aiosqlite | 내부 스레드 풀 | ThreadPoolExecutor |
| SQLite | 단일 연결 | 파일 락 |

---

## 교훈

1. **Pydantic 버전 확인**: `pip show pydantic`으로 버전 확인 후, v2라면 `ConfigDict` 사용
2. **500 디버깅**: FastAPI는 500 발생 시 터미널에 전체 traceback을 출력한다. 브라우저 콘솔만 보지 말고 백엔드 터미널을 먼저 확인할 것
3. **단일 스레드 = 느린 게 아님**: async/await로 I/O 대기 중에도 다른 요청을 처리하므로, CPU 집약적 작업이 아닌 I/O 중심 서비스에서는 충분히 고성능
