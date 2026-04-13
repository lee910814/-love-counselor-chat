from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
from urllib.parse import quote

from crawlers.base import BaseCrawler, CrawledItem


class MBTICrawler(BaseCrawler):
    """MBTI 연애 관련 브런치 크롤러"""

    # 브런치 단일 키워드 (공백 없이)
    KEYWORDS = [
        "MBTI",
        "INFP",
        "INFJ",
        "ENFP",
        "ENFJ",
        "INTJ",
        "INTP",
        "ENTP",
        "ENTJ",
        "ISFP",
        "ISFJ",
        "연애궁합",
    ]

    def __init__(self):
        super().__init__("mbti")

    def _get_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def crawl(self, pages: int = 3, max_items: int = None) -> List[CrawledItem]:
        """MBTI 키워드로 브런치 글 크롤링

        Args:
            pages: 키워드당 스크롤 횟수
            max_items: 최대 수집 수

        Returns:
            크롤링된 아이템 리스트
        """
        items = []
        seen_urls = set()
        driver = None

        try:
            driver = self._get_driver()

            for keyword in self.KEYWORDS:
                if max_items and len(items) >= max_items:
                    break

                encoded = quote(keyword)
                url = f"https://brunch.co.kr/keyword/{encoded}"
                print(f"\n[{keyword}] 수집 중... ({url})")

                try:
                    driver.get(url)
                    time.sleep(3)

                    # 스크롤로 게시물 로드
                    for _ in range(pages):
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)

                    # 게시물 링크 수집
                    post_elements = driver.find_elements(By.CSS_SELECTOR, "a.link_post")
                    post_urls = [
                        e.get_attribute("href") for e in post_elements
                        if e.get_attribute("href") and e.get_attribute("href") not in seen_urls
                    ]
                    print(f"  → {len(post_urls)}개 링크 발견")

                    for i, post_url in enumerate(post_urls):
                        if max_items and len(items) >= max_items:
                            break
                        if post_url in seen_urls:
                            continue

                        seen_urls.add(post_url)

                        try:
                            print(f"  [{i+1}/{len(post_urls)}] 수집 중...")
                            content = self._get_post_content(driver, post_url)
                            if content:
                                items.append(self._create_item(
                                    content=content,
                                    url=post_url,
                                    metadata={"keyword": keyword, "category": "MBTI"}
                                ))
                        except Exception as e:
                            print(f"  글 수집 실패: {e}")

                except Exception as e:
                    print(f"  키워드 페이지 접근 실패: {e}")

            print(f"\n총 {len(items)}개 MBTI 글 수집 완료")

        finally:
            if driver:
                driver.quit()

        return items

    def _get_post_content(self, driver, url: str) -> str:
        try:
            driver.get(url)
            time.sleep(2)
            content_elem = driver.find_element(By.CSS_SELECTOR, "div.wrap_body")
            return content_elem.text.strip()
        except Exception:
            return None
