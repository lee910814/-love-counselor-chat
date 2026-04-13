import json
import os
from embedder import Embedder
from crawlers.base import CrawledItem

def run():
    # 데이터 로드
    with open("chunked_data_50.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # CrawledItem 객체로 변환
    items = [
        CrawledItem(
            content=item["content"],
            source=item["metadata"]["source"],
            url=item["metadata"]["url"],
            metadata=item["metadata"]
        ) for item in data
    ]
    
    # 임베딩 및 저장
    embedder = Embedder()
    # 이미 .env 로드 및 컬렉션 이름 설정이 Embedder.__init__에 있음
    # 컬렉션 이름: love_counselor_ko_sroberta_multitask
    embedder.embed_and_store(items)
    
    # 결과 확인
    info = embedder.get_collection_info()
    print(f"\n최종 컬렉션 상태:")
    print(f"컬렉션 명: {info['name']}")
    print(f"총 포인트 수: {info['points_count']}")

if __name__ == "__main__":
    run()
