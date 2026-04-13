"""
로컬 시맨틱 청커 - API 호출 없이 문장 단위로 의미 청킹
"""
import re
from typing import List


class SemanticChunker:
    """
    문단/문장 단위 시맨틱 청커
    - 외부 API 불필요 (로컬 처리)
    - 한국어 문장 경계 인식
    - 타겟 청크 크기: 300~700자
    """

    def __init__(
        self,
        min_chars: int = 150,
        max_chars: int = 700,
        target_chars: int = 450,
    ):
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.target_chars = target_chars

        # 한국어 문장 분리 패턴
        self._sent_pattern = re.compile(
            r'(?<=[.!?。\n])\s+'
            r'|(?<=[다요죠네까]\.)\s+'
            r'|(?<=[다요죠네까][!?])\s+'
        )

    # ── 공개 API ──────────────────────────────────────────────────

    def chunk(self, text: str) -> List[str]:
        """텍스트를 의미 단위 청크로 분할"""
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.max_chars:
            return [text]

        # 1단계: 빈 줄 기준 문단 분리
        paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]

        # 문단이 하나뿐이면 문장 단위로 내려감
        if len(paragraphs) == 1:
            paragraphs = self._split_sentences(text)

        # 2단계: 문단을 target_chars 기준으로 합치거나 나눔
        return self._merge_paragraphs(paragraphs)

    def chunk_item(self, content: str, metadata: dict) -> List[dict]:
        """
        청킹 후 각 청크에 라벨 메타데이터를 붙여 반환

        반환 형식:
        [
          {
            "content": "...",
            "metadata": {
              ...original_metadata,
              "category": "연애고민",
              "chunk_index": 0,
              "total_chunks": 3,
              "original_length": 1500,
              "is_chunked": True,
            }
          },
          ...
        ]
        """
        chunks = self.chunk(content)
        total = len(chunks)
        category = self._detect_category(content, metadata)

        result = []
        for i, chunk_text in enumerate(chunks):
            m = dict(metadata)
            m.update({
                "category": category,
                "chunk_index": i,
                "total_chunks": total,
                "original_length": len(content),
                "is_chunked": total > 1,
            })
            result.append({"content": chunk_text, "metadata": m})
        return result

    # ── 내부 메서드 ───────────────────────────────────────────────

    def _split_sentences(self, text: str) -> List[str]:
        """문장 단위 분리"""
        raw = self._sent_pattern.split(text)
        sentences = []
        for s in raw:
            s = s.strip()
            if s:
                sentences.append(s)
        return sentences if sentences else [text]

    def _merge_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """문단 리스트를 target_chars 기준으로 병합/분할"""
        chunks: List[str] = []
        buffer = ""

        for para in paragraphs:
            # 단일 문단이 max_chars 초과 → 문장 단위로 재분할
            if len(para) > self.max_chars:
                if buffer:
                    chunks.append(buffer.strip())
                    buffer = ""
                chunks.extend(self._split_long_text(para))
                continue

            joined = (buffer + "\n\n" + para).strip() if buffer else para

            if len(joined) > self.target_chars and len(buffer) >= self.min_chars:
                # 현재 버퍼 확정
                chunks.append(buffer.strip())
                buffer = para
            else:
                buffer = joined

        if buffer.strip():
            chunks.append(buffer.strip())

        return [c for c in chunks if len(c) >= 50]

    def _split_long_text(self, text: str) -> List[str]:
        """max_chars 초과 텍스트를 문장 단위로 분할 후 재병합"""
        sentences = self._split_sentences(text)
        return self._merge_paragraphs(sentences)

    def _detect_category(self, text: str, metadata: dict) -> str:
        """키워드 기반 카테고리 자동 감지"""
        # 메타데이터에 이미 category가 있으면 사용
        if metadata.get("category") and metadata["category"] not in ("", "unknown"):
            existing = metadata["category"]
            # "MBTI" 키워드가 metadata에 있으면 유지
            if existing == "MBTI":
                return "MBTI"

        # keyword 필드 활용
        keyword = str(metadata.get("keyword", "")).upper()
        mbti_types = {
            "MBTI", "INTJ", "INTP", "ENTJ", "ENTP",
            "INFJ", "INFP", "ENFJ", "ENFP",
            "ISTJ", "ISFJ", "ESTJ", "ESFJ",
            "ISTP", "ISFP", "ESTP", "ESFP",
        }
        if keyword in mbti_types or any(t in text.upper() for t in mbti_types):
            return "MBTI"

        # 본문 키워드 매핑
        rules = [
            ("이별",    ["이별", "헤어", "이별하", "차였", "헤어졌", "전남친", "전여친", "전 남친", "전 여친"]),
            ("연락",    ["연락", "답장", "카톡", "문자", "읽씹", "안읽씹", "연락이", "연락을"]),
            ("고백",    ["고백", "소개팅", "썸", "대시", "좋아한다", "사귀자", "사귀고 싶"]),
            ("결혼",    ["결혼", "프러포즈", "청혼", "약혼", "웨딩"]),
            ("데이트",  ["데이트", "만남", "만나자", "약속", "여행", "데이트 코스"]),
            ("질투/바람", ["바람", "浮気", "외도", "질투", "의심", "불륜"]),
            ("장거리",  ["장거리", "원거리", "LDR"]),
        ]
        text_lower = text.lower()
        for category, keywords in rules:
            if any(kw in text_lower for kw in keywords):
                return category

        return "연애고민"
