# [트러블슈팅] /api/sessions/ 404 Not Found

> 작성일: 2026-04-13  
> 프로젝트: RAG 기반 연애 상담 챗봇  
> 스택: FastAPI · React · Vite · SQLAlchemy · aiosqlite

---

## 문제 상황

대화 저장 기능을 위해 `/api/sessions/` 엔드포인트를 추가한 뒤,  
사용자가 메시지를 전송하자 브라우저 콘솔에 다음 에러가 연속으로 출력됐다.

```
:5174/api/sessions/:1  Failed to load resource: the server responded with a status of 404 (Not Found)
App.tsx:100 Uncaught (in promise) AxiosError: Request failed with status code 404
    at settle (settle.js:20:7)
    at XMLHttpRequest.onloadend (xhr.js:62:9)
```

---

## 원인 분석

### 1. Stale Background Server — 구버전 서버의 포트 점유

세션 기능을 추가하기 이전, 개발 편의를 위해 백그라운드 프로세스로 uvicorn 서버를 띄워두었다.  
이 서버는 `sessions_router`가 `main.py`에 등록되기 전에 시작됐기 때문에, 코드를 수정해도 해당 라우트가 존재하지 않는 채로 계속 실행됐다.

```
# 포트 8000에서 응답 중인 서버의 실제 라우트
GET  /api/chat/
POST /api/chat/stream
GET  /api/chat/health
# /api/sessions/ 없음
```

### 2. WatchFiles Hot Reload 미동작 (Windows 환경)

uvicorn의 `--reload` 옵션은 내부적으로 **WatchFiles** 라이브러리를 사용해 파일 변경을 감지한다.  
그런데 Windows + Git Bash 환경에서는 파일 시스템 이벤트(FSEvent)를 누락하는 버그가 있다.

- `debug_chat.py` 수정 → 감지 성공, 리로드 발생
- `main.py`, `sessions.py`, `api/__init__.py` 수정 → **감지 실패**, 리로드 없음

결과적으로 서버는 세션 라우트가 없는 구버전 코드로 계속 실행됐다.

```
# 서버 로그
WatchFiles detected changes in 'debug_chat.py'. Reloading...  ← 1회만 발생
# 이후 main.py 변경은 감지되지 않음
```

### 3. 신규 서버 포트 바인딩 실패

구버전 서버가 8000 포트를 점유한 상태에서 새 서버를 `--port 8000`으로 시작하면  
`[Errno 10048] Only one usage of each socket address is permitted` 에러와 함께 바인딩에 실패한다.  
결과적으로 프론트는 여전히 구버전 서버와 통신하게 됐다.

### 4. Vite 포트 충돌 → 5174 포트 사용

구버전 Vite 서버(5173)도 살아있어, 새 Vite 서버가 자동으로 **5174** 포트를 사용했다.  
에러 로그에 `:5174`가 찍힌 이유가 이것이다.

---

## 원인 요약

```
[구버전 서버, 포트 8000 점유]
    ↓ sessions_router 없음
    ↓ WatchFiles가 main.py 변경 감지 못함
    ↓ 새 서버가 8000에 바인딩 실패

[프론트 → 구버전 서버]
    /api/sessions/ → 404 Not Found
```

---

## 해결 방법

구버전 서버의 포트 점유 문제를 원천 차단하기 위해 **백엔드 포트를 8001로 고정**하고,  
Vite 프록시 설정도 함께 변경했다.

### 1. `vite.config.ts` 프록시 수정

```ts
// before
target: 'http://localhost:8000'

// after
target: 'http://localhost:8001'
```

### 2. 백엔드 실행 포트 고정

```python
# app/main.py
uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
```

```bash
# 터미널에서 직접 실행 시
uvicorn app.main:app --reload --port 8001
```

---

## 재발 방지

백그라운드 프로세스로 서버를 관리하면 재시작·종료 제어가 어렵다.  
**개발 중에는 반드시 터미널에서 직접 서버를 실행**하고, 코드 변경 후에는 Ctrl+C 후 재시작으로 확인한다.

```bash
# 터미널 1 — 백엔드
cd backend
source venv/Scripts/activate
uvicorn app.main:app --reload --port 8001

# 터미널 2 — 프론트
cd frontend
npm run dev
```

---

## 교훈

| 항목 | 내용 |
|------|------|
| WatchFiles | Windows에서 파일 이벤트 누락 가능 → 수동 재시작으로 확인 |
| 포트 점유 | 기존 프로세스 확인 후 서버 시작 (`netstat -ano \| grep 8000`) |
| 서버 관리 | 개발 서버는 터미널에서 직접 실행, 백그라운드 실행 지양 |
