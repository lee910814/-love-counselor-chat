import os
import sys

# 환경 변수 설정
os.environ['PYTHONPATH'] = '.'
os.environ['EMBEDDING_MODEL'] = 'jhgan/ko-sroberta-multitask'

from app.services.qdrant_service import get_qdrant_service

def test_search():
    try:
        s = get_qdrant_service()
        query = "권태기 극복하는 법 알려줘"
        print(f"검색어: {query}")
        
        res = s.search(query, top_k=3)
        print("\n[검색 결과]")
        for i, r in enumerate(res):
            content = r["content"].replace('\n', ' ')
            print(f"{i+1}. {content[:150]}...")
            print(f"   (점수: {r['score']:.4f}, 출처: {r['metadata'].get('source')})")
            
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    test_search()
