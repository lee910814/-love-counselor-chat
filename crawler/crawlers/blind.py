from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

from crawlers.base import BaseCrawler, CrawledItem


class BlindCrawler(BaseCrawler):
    """블라인드 크롤러"""

    def __init__(self):
        super().__init__("blind")
        # 연애·결혼 토픽 (올바른 URL 인코딩)
        self.base_url = "https://www.teamblind.com/kr/topics/%EC%97%B0%EC%95%A0%C2%B7%EA%B2%B0%ED%98%BC"

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

    def crawl(self, pages: int = 2, max_items: int = None) -> List[CrawledItem]:
        items = []
        driver = None
        try:
            driver = self._get_driver()
            # 블라인드는 메인 페이지에서 스크롤로 더 많은 내용을 가져옴
            driver.get(self.base_url)
            time.sleep(3)

            # 페이지 스크롤 처리
            for _ in range(pages - 1):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            # 게시물 링크 수집 (다중 셀렉터 시도)
            selectors = [
                "div.article-list-item a.lb",
                "a.article-list-item",
                "ul.article-list li a",
                "div[class*='article'] a[href*='/post/']",
            ]
            post_urls = []
            for sel in selectors:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                urls = [e.get_attribute("href") for e in elems if e.get_attribute("href")]
                if urls:
                    post_urls = list(dict.fromkeys(urls))  # 중복 제거
                    break
            print(f"Blind에서 {len(post_urls)}개의 글 링크를 발견했습니다.")

            for i, post_url in enumerate(post_urls):
                if max_items and len(items) >= max_items:
                    print(f"Blind 수집 제한({max_items})에 도달했습니다.")
                    break
                    
                try:
                    print(f"[{i+1}/{len(post_urls)}] {post_url} 수집 중...")
                    content = self._get_post_content(driver, post_url)
                    if content:
                        items.append(self._create_item(
                            content=content,
                            url=post_url,
                            metadata={"topic": "dating_marriage"}
                        ))
                except Exception as e:
                    print(f"Error getting Blind post: {e}")

        finally:
            if driver:
                driver.quit()

        return items

    def _get_post_content(self, driver, url: str) -> str:
        try:
            driver.get(url)
            time.sleep(2)
            for sel in ["div#article-contents", "div.article-body", "div#content", "div[class*='content']"]:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, sel)
                    text = elem.text.strip()
                    if text:
                        return text
                except Exception:
                    continue
            return None
        except Exception:
            return None
