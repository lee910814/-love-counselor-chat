from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class CrawledItem:
    """크롤링된 아이템"""
    content: str
    source: str  # 출처 (youtube, dcinside, instiz, mbti)
    url: str
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "metadata": {
                "source": self.source,
                "url": self.url,
                **(self.metadata or {})
            }
        }


class BaseCrawler(ABC):
    """크롤러 베이스 클래스"""

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    def crawl(self, **kwargs) -> List[CrawledItem]:
        """크롤링 실행

        Returns:
            크롤링된 아이템 리스트
        """
        pass

    def _create_item(
        self,
        content: str,
        url: str,
        metadata: Dict[str, Any] = None
    ) -> CrawledItem:
        """CrawledItem 생성 헬퍼"""
        return CrawledItem(
            content=content,
            source=self.source_name,
            url=url,
            metadata=metadata
        )
