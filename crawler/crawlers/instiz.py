from typing import List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

from crawlers.base import BaseCrawler, CrawledItem


class InstizCrawler(BaseCrawler):
    """인스티즈 크롤러"""

    def __init__(self):
        super().__init__("instiz")
        self.base_url = "https://www.instiz.net"

    def _get_driver(self):
        """Selenium 드라이버 생성"""
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

    def crawl(
        self,
        board: str = "pt",  # 사랑/연애 게시판
        pages: int = 5
    ) -> List[CrawledItem]:
        """인스티즈 게시판 크롤링

        Args:
            board: 게시판 코드 (pt: 사랑/연애)
            pages: 크롤링할 페이지 수

        Returns:
            크롤링된 아이템 리스트
        """
        items = []
        driver = None

        try:
            driver = self._get_driver()

            for page in range(1, pages + 1):
                url = f"{self.base_url}/{board}?page={page}"

                try:
                    driver.get(url)
                    time.sleep(2)

                    # 게시물 링크 수집
                    post_elements = driver.find_elements(
                        By.CSS_SELECTOR,
                        ".listsubject a"
                    )

                    post_urls = []
                    for elem in post_elements:
                        href = elem.get_attribute("href")
                        if href and "/pt/" in href:
                            post_urls.append(href)

                    for post_url in post_urls[:20]:
                        try:
                            content = self._get_post_content(driver, post_url)
                            if content:
                                items.append(self._create_item(
                                    content=content,
                                    url=post_url,
                                    metadata={"board": board, "page": page}
                                ))
                        except Exception as e:
                            print(f"Error getting post: {e}")

                except Exception as e:
                    print(f"Error crawling page {page}: {e}")

        finally:
            if driver:
                driver.quit()

        return items

    def _get_post_content(self, driver, url: str) -> str:
        """게시물 본문 가져오기"""
        try:
            driver.get(url)
            time.sleep(1)

            content_elem = driver.find_element(
                By.CSS_SELECTOR,
                ".memo_content"
            )
            return content_elem.text.strip()
        except Exception:
            return None
