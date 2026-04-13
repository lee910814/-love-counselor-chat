from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat_router
from app.config import get_settings

app = FastAPI(
    title="연애 상담 챗봇 API",
    description="RAG 기반 연애 상담 챗봇 백엔드",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "message": "연애 상담 챗봇 API",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )
