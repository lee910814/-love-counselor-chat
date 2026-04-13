# 연애 상담 챗봇

RAG(Retrieval-Augmented Generation) 기반 연애 상담 AI 챗봇입니다.  
실제 연애 커뮤니티 데이터를 벡터 DB에 저장하고, 사용자 질문과 유사한 사례를 검색해 LLM이 맥락 있는 답변을 생성합니다.

---

## 주요 기능

- **RAG 기반 상담** — 실제 커뮤니티 사례 검색 후 LLM 응답 생성
- **스트리밍 응답** — SSE(Server-Sent Events)로 토큰 단위 실시간 출력
- **회원/비회원 모드** — JWT 인증, 비회원도 바로 사용 가능
- **대화 저장** — 로그인 시 대화 세션 자동 저장 및 불러오기
- **반응형 UI** — 사이드바 대화 목록, 날짜/시간 표시

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Frontend | React 18 · TypeScript · Vite · Tailwind CSS · React Query |
| Backend | FastAPI · Python 3.12 · SQLAlchemy 2.0 · aiosqlite |
| 인증 | JWT (python-jose) · bcrypt (passlib) |
| Vector DB | Qdrant |
| LLM | Qwen2.5-14B-Instruct → gemma-2-9b-it (fallback) via HuggingFace |
| Embedding | `jhgan/ko-sroberta-multitask` (한국어 특화) |
| 크롤링 | Blind · DC인사이드 · Brunch · ELLE · MBTI 커뮤니티 |

---

## 아키텍처

```
사용자 메시지
    ↓
[Embedding] → 벡터 변환
    ↓
[Qdrant] → 유사 문서 검색 (top-8, score ≥ 0.45, 최대 3개)
    ↓
[HuggingFace LLM] → 컨텍스트 포함 답변 생성 (SSE 스트리밍)
    ↓
사용자 화면 (토큰 단위 실시간 출력)
```

---

## 프로젝트 구조

```
love-counselor/
├── frontend/
│   └── src/
│       ├── components/       # ChatWindow · MessageBubble · InputBox · Sidebar
│       ├── context/          # AuthContext (JWT · 비회원 모드)
│       ├── pages/            # AuthPage (로그인/회원가입)
│       └── services/         # API 통신 (axios)
├── backend/
│   └── app/
│       ├── api/              # chat · sessions · auth 라우터
│       ├── services/         # RAG · HuggingFace · Qdrant · auth
│       ├── database.py       # SQLAlchemy 모델 (User · ChatSession · ChatMessage)
│       └── config.py
├── crawler/                  # 데이터 수집 파이프라인
├── docs/                     # 트러블슈팅 기술 블로그
├── docker-compose.yml        # Qdrant 컨테이너
└── .env.example
```

---

## 시작하기

### 1. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 필수 항목:

```env
HUGGINGFACE_API_KEY=your_key
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=love_counselor
EMBEDDING_MODEL=jhgan/ko-sroberta-multitask
```

### 2. Qdrant 실행 (Docker 필요)

```bash
docker-compose up -d
```

### 3. 백엔드 실행

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 4. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 5. 데이터 수집 (선택)

```bash
cd crawler
pip install -r requirements.txt
python run_pipeline.py   # 크롤링 + 임베딩 + Qdrant 업로드
```

---

## API

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| POST | `/api/auth/register` | - | 회원가입 → JWT 반환 |
| POST | `/api/auth/login` | - | 로그인 → JWT 반환 |
| GET | `/api/auth/me` | 필요 | 내 정보 조회 |
| POST | `/api/chat/stream` | - | SSE 스트리밍 채팅 |
| GET | `/api/sessions/` | 필요 | 대화 세션 목록 |
| POST | `/api/sessions/` | 필요 | 새 세션 생성 |
| GET | `/api/sessions/{id}` | 필요 | 세션 상세 조회 |
| DELETE | `/api/sessions/{id}` | 필요 | 세션 삭제 |
| GET | `/docs` | - | Swagger UI |

---

## 주의사항

- `.env` 파일은 절대 커밋하지 마세요 (`.gitignore` 포함)
- HuggingFace Inference API 무료 플랜은 요청 제한이 있어요
- 크롤링 시 각 사이트의 이용약관과 `robots.txt`를 확인하세요
