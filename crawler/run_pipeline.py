"""
크롤링 → 전처리 → 시맨틱 청킹 → 라벨링 → Qdrant 임베딩 통합 파이프라인

사용법:
    python run_pipeline.py --sources brunch dcinside instiz blind mbti
    python run_pipeline.py --sources dcinside --pages 3
    python run_pipeline.py --sources all --pages 5
    python run_pipeline.py --dry-run   # 임베딩 없이 결과만 확인
"""
import argparse
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import os

from crawlers import (
    CrawledItem, BrunchCrawler, DCInsideCrawler,
    InstizCrawler, MBTICrawler, BlindCrawler,
)
from preprocessor import TextPreprocessor
from semantic_chunker import SemanticChunker

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────────

QDRANT_HOST       = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_BASE   = os.getenv("QDRANT_COLLECTION_NAME", "love_counselor")
EMBEDDING_MODEL   = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")

# ── 크롤러 실행 ───────────────────────────────────────────────────

def crawl_source(source: str, pages: int) -> List[CrawledItem]:
    print(f"\n{'='*50}")
    print(f"[{source.upper()}] 크롤링 시작 (pages={pages})")
    print('='*50)

    try:
        if source == "brunch":
            return BrunchCrawler().crawl(pages=pages)

        elif source == "dcinside":
            return DCInsideCrawler().crawl(pages=pages)

        elif source == "instiz":
            return InstizCrawler().crawl(pages=pages)

        elif source == "blind":
            return BlindCrawler().crawl(pages=pages)

        elif source == "mbti":
            return MBTICrawler().crawl(pages=pages)

    except Exception as e:
        print(f"[{source}] 크롤링 오류: {e}")

    return []


# ── 청킹 + 라벨링 ─────────────────────────────────────────────────

def chunk_and_label(items: List[CrawledItem]) -> List[Dict[str, Any]]:
    chunker = SemanticChunker(min_chars=150, max_chars=700, target_chars=450)
    results = []

    for item in items:
        metadata = {
            "source":   item.source,
            "url":      item.url,
            **(item.metadata or {}),
        }
        chunks = chunker.chunk_item(item.content, metadata)
        results.extend(chunks)

    return results


# ── 임베딩 & Qdrant 저장 ─────────────────────────────────────────

def embed_and_store(chunks: List[Dict[str, Any]], dry_run: bool = False):
    model_sanitized = EMBEDDING_MODEL.split("/")[-1].replace("-", "_")
    collection_name = f"{COLLECTION_BASE}_{model_sanitized}"

    print(f"\n임베딩 모델 로드: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    vector_size = model.get_sentence_embedding_dimension()

    if dry_run:
        print(f"[DRY RUN] {len(chunks)}개 청크를 임베딩 없이 확인만 합니다.")
        _print_sample(chunks)
        return

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # 컬렉션 생성 (없으면)
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        print(f"컬렉션 생성: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    else:
        print(f"컬렉션 사용: {collection_name}")

    batch_size = 64
    stored = 0

    for i in tqdm(range(0, len(chunks), batch_size), desc="임베딩 저장"):
        batch = chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]
        vectors = model.encode(texts, show_progress_bar=False)

        points = []
        for chunk, vec in zip(batch, vectors):
            payload = {
                "content":         chunk["content"],
                "source":          chunk["metadata"].get("source", ""),
                "url":             chunk["metadata"].get("url", ""),
                "category":        chunk["metadata"].get("category", "연애고민"),
                "keyword":         chunk["metadata"].get("keyword", ""),
                "chunk_index":     chunk["metadata"].get("chunk_index", 0),
                "total_chunks":    chunk["metadata"].get("total_chunks", 1),
                "original_length": chunk["metadata"].get("original_length", len(chunk["content"])),
                "is_chunked":      chunk["metadata"].get("is_chunked", False),
                "crawled_at":      datetime.now().isoformat(),
            }
            # 소스별 추가 필드
            for key in ("gallery", "gallery_name", "board", "topic"):
                if chunk["metadata"].get(key):
                    payload[key] = chunk["metadata"][key]

            points.append(PointStruct(id=str(uuid.uuid4()), vector=vec.tolist(), payload=payload))

        client.upsert(collection_name=collection_name, points=points)
        stored += len(points)

    # 저장 후 통계
    info = client.get_collection(collection_name)
    print(f"\n저장 완료: {stored}개 청크")
    print(f"컬렉션 총 포인트: {info.points_count}개")


def _print_sample(chunks: List[Dict[str, Any]]):
    print(f"\n{'='*50}")
    print(f"[샘플] 처음 3개 청크 미리보기")
    print('='*50)
    for c in chunks[:3]:
        m = c["metadata"]
        print(f"  source   : {m.get('source')}")
        print(f"  category : {m.get('category')}")
        print(f"  chunk    : {m.get('chunk_index')+1}/{m.get('total_chunks')}")
        print(f"  length   : {len(c['content'])}자")
        print(f"  content  : {c['content'][:80]}...")
        print()


# ── 카테고리 분포 출력 ────────────────────────────────────────────

def print_stats(chunks: List[Dict[str, Any]]):
    from collections import Counter
    cats = Counter(c["metadata"].get("category", "?") for c in chunks)
    srcs = Counter(c["metadata"].get("source", "?") for c in chunks)

    print(f"\n{'='*50}")
    print(f"총 청크: {len(chunks)}개")
    print("\n[카테고리 분포]")
    for cat, cnt in cats.most_common():
        print(f"  {cat:<12}: {cnt}개")
    print("\n[소스 분포]")
    for src, cnt in srcs.most_common():
        print(f"  {src:<12}: {cnt}개")
    print('='*50)


# ── 메인 ──────────────────────────────────────────────────────────

ALL_SOURCES = ["brunch", "dcinside", "instiz", "blind", "mbti"]


def main():
    parser = argparse.ArgumentParser(description="연애 상담 데이터 수집 파이프라인")
    parser.add_argument(
        "--sources", nargs="+",
        choices=ALL_SOURCES + ["all"],
        default=["brunch"],
        help="크롤링할 소스 (복수 선택 가능, all=전체)",
    )
    parser.add_argument("--pages", type=int, default=3, help="소스당 크롤링 페이지 수")
    parser.add_argument("--dry-run", action="store_true", help="임베딩 저장 없이 결과만 확인")
    parser.add_argument("--save-json", action="store_true", help="청킹 결과를 JSON으로 저장")
    args = parser.parse_args()

    sources = ALL_SOURCES if "all" in args.sources else args.sources

    # 1. 크롤링
    all_items: List[CrawledItem] = []
    for source in sources:
        items = crawl_source(source, args.pages)
        all_items.extend(items)
        print(f"[{source}] {len(items)}개 수집")

    if not all_items:
        print("수집된 데이터가 없습니다.")
        return

    print(f"\n총 수집: {len(all_items)}개")

    # 2. 전처리
    print("\n=== 전처리 ===")
    preprocessor = TextPreprocessor()
    cleaned = preprocessor.process(all_items)

    # 3. 시맨틱 청킹 + 라벨링
    print(f"\n=== 시맨틱 청킹 ===")
    chunks = chunk_and_label(cleaned)
    print(f"청킹 완료: {len(cleaned)}개 → {len(chunks)}개 청크")

    # 4. 통계 출력
    print_stats(chunks)

    # 5. JSON 저장 (선택)
    if args.save_json:
        filename = f"pipeline_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"\nJSON 저장: {filename}")

    # 6. 임베딩 & Qdrant 저장
    print("\n=== 임베딩 & Qdrant 저장 ===")
    embed_and_store(chunks, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
