from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

from crawlers.base import BaseCrawler, CrawledItem


class BrunchCrawler(BaseCrawler):
    """브런치 크롤러"""

    def __init__(self):
        super().__init__("brunch")
        self.base_url = "https://brunch.co.kr/keyword/%EC%97%B0%EC%95%A0"

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

    def crawl(self, pages: int = 1, max_items: int = None) -> List[CrawledItem]:
        items = []
        driver = None
        try:
            driver = self._get_driver()
            driver.get(self.base_url)
            time.sleep(3)

            # 브런치는 스크롤로 게시물을 로드함
            for _ in range(pages):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            # 게시물 링크 수집
            post_elements = driver.find_elements(By.CSS_SELECTOR, "a.link_post")
            post_urls = [elem.get_attribute("href") for elem in post_elements if elem.get_attribute("href")]
            print(f"Brunch에서 {len(post_urls)}개의 글 링크를 발견했습니다.")

            for i, post_url in enumerate(post_urls):
                if max_items and len(items) >= max_items:
                    print(f"Brunch 수집 제한({max_items})에 도달했습니다.")
                    break
                    
                try:
                    print(f"[{i+1}/{len(post_urls)}] {post_url} 수집 중...")
                    content = self._get_post_content(driver, post_url)
                    if content:
                        items.append(self._create_item(
                            content=content,
                            url=post_url,
                            metadata={"keyword": "연애"}
                        ))
                except Exception as e:
                    print(f"Error getting Brunch post: {e}")

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
