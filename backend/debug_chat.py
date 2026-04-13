import os
from app.api.chat import ChatRequest, Message
from app.services.rag_service import get_rag_service
import asyncio

async def debug_chat():
    os.environ['HUGGINGFACE_API_KEY'] = os.getenv('HUGGINGFACE_API_KEY', '')
    os.environ['EMBEDDING_MODEL'] = 'jhgan/ko-sroberta-multitask'
    os.environ['QDRANT_HOST'] = 'localhost'
    os.environ['QDRANT_PORT'] = '6333'
    os.environ['QDRANT_COLLECTION_NAME'] = 'love_counselor'
    
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
