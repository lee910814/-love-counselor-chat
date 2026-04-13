import os
from dotenv import load_dotenv
from app.api.chat import ChatRequest, Message
from app.services.rag_service import get_rag_service
import asyncio

load_dotenv()

async def debug_chat():
    # 환경변수는 .env에서 자동 로드됨 (HUGGINGFACE_API_KEY, ANTHROPIC_API_KEY 등)
    
    print("RAG 서비스 초기화 중...")
    rag_service = get_rag_service()
    
    user_message = "권태기 극복하는 법 알려줘"
    print(f"사용자 메시지: {user_message}")
    
    try:
        result = rag_service.get_response(
            user_message=user_message,
            chat_history=None
        )
        print("\n응답 결과:")
        print(result["response"])
    except Exception as e:
        print("\n[에러 발생]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_chat())
