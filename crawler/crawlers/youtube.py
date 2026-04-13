from typing import List
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import requests
import re

from crawlers.base import BaseCrawler, CrawledItem


class YouTubeCrawler(BaseCrawler):
    """유튜브 자막/댓글 크롤러"""

    def __init__(self, api_key: str = None):
        super().__init__("youtube")
        self.api_key = api_key

    def crawl(
        self,
        video_ids: List[str] = None,
        search_query: str = "연애 상담",
        max_results: int = 10
    ) -> List[CrawledItem]:
        """유튜브 영상 자막 크롤링

        Args:
            video_ids: 크롤링할 비디오 ID 리스트
            search_query: 검색어 (video_ids가 없을 때 사용)
            max_results: 최대 결과 수

        Returns:
            크롤링된 아이템 리스트
        """
        items = []

        if video_ids is None:
            video_ids = self._get_sample_video_ids()

        for video_id in video_ids[:max_results]:
            try:
                transcript = self._get_transcript(video_id)
                if transcript:
                    items.append(self._create_item(
                        content=transcript,
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        metadata={"video_id": video_id}
                    ))
            except Exception as e:
                print(f"Error crawling video {video_id}: {e}")

        return items

    def _get_transcript(self, video_id: str) -> str:
        """영상 자막 가져오기"""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['ko', 'en']
            )
            return " ".join([item['text'] for item in transcript_list])
        except (TranscriptsDisabled, NoTranscriptFound):
            return None

    def _get_sample_video_ids(self) -> List[str]:
        """샘플 연애 상담 비디오 ID (테스트용)"""
        return [
            # 실제 사용 시 YouTube Data API로 검색하여 가져옴
        ]
