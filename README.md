# 연애 상담 챗봇

RAG(Retrieval-Augmented Generation) 기반 연애 상담 챗봇입니다.  
실제 연애 관련 커뮤니티 데이터를 벡터 DB에 저장하고, 사용자의 질문과 유사한 문서를 검색해 LLM이 답변을 생성합니다.

## 기술 스택

| 분류 | 기술 |
|------|------|
| Frontend | React 18 + TypeScript + Tailwind CSS + Vite |
| Backend | FastAPI + Python 3.12 |
| Vector DB | Qdrant |
| LLM | Qwen2.5-14B-Instruct (fallback: gemma-2-9b-it) via HuggingFace Inference API |
| Embedding | `jhgan/ko-sroberta-multitask` (한국어 특화) |
| 크롤링 | Blind, DC인사이드, Brunch, ELLE, MBTI 커뮤니티 등 |

## 아키텍처

```
사용자 메시지
    ↓
[Embedding 모델] → 벡터 변환
    ↓
[Qdrant 벡터 검색] → 유사 문서 top-8 추출 (score ≥ 0.45 필터링, 최대 3개)
    ↓
[HuggingFace LLM] → 컨텍스트 + 메시지로 답변 생성 (스트리밍)
    ↓
사용자 응답 (SSE 스트리밍)
```

## 프로젝트 구조

```
love-counselor/
├── frontend/               # React 앱
│   └── src/
│       ├── components/     # ChatWindow, InputBox, MessageBubble
│       └── services/       # API 통신 (axios)
├── backend/
│   └── app/
│       ├── api/            # FastAPI 라우터
│       ├── services/
│       │   ├── rag_service.py        # RAG 핵심 로직
│       │   ├── qdrant_service.py     # 벡터 검색
│       │   └── huggingface_service.py # LLM 호출
│       └── config.py
├── crawler/                # 데이터 수집 파이프라인
│   └── crawlers/           # 사이트별 크롤러
├── docker-compose.yml      # Qdrant 컨테이너
└── .env.example            # 환경변수 예시
```

## 시작하기

### 1. 환경변수 설정

```bash
cp .env.example .env
# .env 파일에서 API 키 입력
```

`.env` 필수 항목:

```env
ANTHROPIC_API_KEY=your_key       # (선택) Claude API
HUGGINGFACE_API_KEY=your_key     # HuggingFace Inference API 키
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=love_counselor
EMBEDDING_MODEL=jhgan/ko-sroberta-multitask
```

### 2. Qdrant 실행

```bash
docker-compose up -d
```

### 3. 백엔드 실행

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
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
python main.py --sample        # 샘플 데이터 테스트
python run_pipeline.py         # 전체 크롤링 + 임베딩 + Qdrant 업로드
```

## API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/chat/` | 채팅 메시지 전송 |
| GET | `/api/chat/stream` | SSE 스트리밍 응답 |
| GET | `/api/chat/health` | 헬스 체크 |
| GET | `/docs` | Swagger UI |

## 주의사항

- `.env` 파일은 절대 커밋하지 마세요 (`.gitignore`에 포함됨)
- 크롤링 시 각 사이트의 이용약관과 `robots.txt`를 확인하세요
