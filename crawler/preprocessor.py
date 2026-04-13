import re
from typing import List, Set

from crawlers.base import CrawledItem


class TextPreprocessor:
    """텍스트 전처리기 - 부적절한 언어 필터링"""

    def __init__(self):
        # 필터링할 부적절한 단어 리스트 (기본)
        self.bad_words: Set[str] = self._load_bad_words()

        # 최소 텍스트 길이
        self.min_length = 20

        # 최대 텍스트 길이
        self.max_length = 2000

    def _load_bad_words(self) -> Set[str]:
        """부적절한 단어 로드"""
        # 기본 욕설/비속어 패턴 (필요에 따라 확장)
        bad_words = {
            # 일반적인 욕설 패턴
            "시발", "씨발", "ㅅㅂ", "ㅆㅂ",
            "병신", "ㅂㅅ",
            "지랄", "ㅈㄹ",
            "새끼", "ㅅㄲ",
            "개새", "좆", "ㅈ같",
            # 추가적인 비속어는 별도 파일로 관리 권장
        }
        return bad_words

    def load_bad_words_from_file(self, filepath: str):
        """파일에서 부적절한 단어 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                words = {line.strip() for line in f if line.strip()}
                self.bad_words.update(words)
        except FileNotFoundError:
            print(f"Bad words file not found: {filepath}")

    def contains_bad_words(self, text: str) -> bool:
        """텍스트에 부적절한 단어 포함 여부"""
        text_lower = text.lower()
        for word in self.bad_words:
            if word.lower() in text_lower:
                return True
        return False

    def clean_text(self, text: str) -> str:
        """텍스트 정제"""
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)

        # URL 제거
        text = re.sub(r'http[s]?://\S+', '', text)

        # 이메일 제거
        text = re.sub(r'\S+@\S+', '', text)

        # 연속된 공백 정리
        text = re.sub(r'\s+', ' ', text)

        # 특수문자 과다 제거 (이모티콘 등)
        text = re.sub(r'[^\w\s가-힣.,!?~ㄱ-ㅎㅏ-ㅣ]', '', text)

        return text.strip()

    def is_valid_content(self, text: str) -> bool:
        """유효한 콘텐츠인지 검증"""
        # 길이 체크
        if len(text) < self.min_length:
            return False
        if len(text) > self.max_length:
            return False

        # 부적절한 단어 체크
        if self.contains_bad_words(text):
            return False

        # 광고성 콘텐츠 패턴 체크
        ad_patterns = [
            r'카톡|카카오톡.*상담',
            r'텔레그램.*문의',
            r'010-\d{4}-\d{4}',
            r'돈.*벌',
            r'수익.*보장',
        ]
        for pattern in ad_patterns:
            if re.search(pattern, text):
                return False

        return True

    def process(self, items: List[CrawledItem]) -> List[CrawledItem]:
        """크롤링된 아이템 전처리

        Args:
            items: 크롤링된 아이템 리스트

        Returns:
            전처리된 아이템 리스트
        """
        processed = []

        for item in items:
            # 텍스트 정제
            cleaned_content = self.clean_text(item.content)

            # 유효성 검증
            if self.is_valid_content(cleaned_content):
                processed.append(CrawledItem(
                    content=cleaned_content,
                    source=item.source,
                    url=item.url,
                    metadata=item.metadata
                ))

        print(f"전처리 완료: {len(items)}개 -> {len(processed)}개 (필터링: {len(items) - len(processed)}개)")
        return processed
