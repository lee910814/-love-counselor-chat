from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

from crawlers.base import BaseCrawler, CrawledItem


class DCInsideCrawler(BaseCrawler):
    """디시인사이드 마이너 갤러리 크롤러"""

    # 확인된 유효 갤러리 ID → (label, category)
    GALLERIES: Dict[str, tuple] = {
        "some":    ("썸", "고백"),
        "couple":  ("커플", "연애고민"),
        "mbti":    ("MBTI", "MBTI"),
        "infp":    ("INFP", "MBTI"),
        "enfp":    ("ENFP", "MBTI"),
        "breakup": ("이별/재회", "이별"),
    }

    def __init__(self):
        super().__init__("dcinside")
        self.mgallery_url = "https://gall.dcinside.com/mgallery/board/lists/?id={gid}&page={page}"
        self.post_base    = "https://gall.dcinside.com"

    def _get_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def _dismiss_alert(self, driver) -> bool:
        """팝업 알림 처리. 갤러리 폐쇄 알림이면 True 반환"""
        try:
            alert = driver.switch_to.alert
            text = alert.text
            alert.accept()
            if "폐쇄" in text or "운영원칙" in text:
                return True
        except Exception:
            pass
        return False

    def crawl(
        self,
        gallery_ids: List[str] = None,
        pages: int = 3,
        posts_per_page: int = 20,
    ) -> List[CrawledItem]:
        """
        Args:
            gallery_ids: 수집할 갤러리 ID 리스트. None이면 GALLERIES 전체
            pages: 갤러리당 수집 페이지 수
            posts_per_page: 페이지당 최대 게시물 수
        """
        if gallery_ids is None:
            gallery_ids = list(self.GALLERIES.keys())

        items = []
        driver = None

        try:
            driver = self._get_driver()

            for gid in gallery_ids:
                label, category = self.GALLERIES.get(gid, (gid, "연애고민"))
                print(f"\n[DC/{gid}] '{label}' 갤러리 수집 중...")
                gallery_items = 0

                for page in range(1, pages + 1):
                    url = self.mgallery_url.format(gid=gid, page=page)
                    try:
                        driver.get(url)
                        time.sleep(2)

                        if self._dismiss_alert(driver):
                            print(f"  [DC/{gid}] 갤러리 폐쇄됨, 건너뜀")
                            break

                        post_links = driver.find_elements(
                            By.CSS_SELECTOR, "tr.ub-content .gall_tit a:first-child"
                        )
                        urls = [
                            l.get_attribute("href") for l in post_links[:posts_per_page]
                            if l.get_attribute("href")
                        ]
                        print(f"  페이지 {page}: {len(urls)}개 링크")

                        for post_url in urls:
                            try:
                                content = self._get_post_content(driver)
                                if not content:
                                    driver.get(post_url)
                                    time.sleep(1.5)
                                    content = self._get_post_content(driver)
                                if content:
                                    items.append(self._create_item(
                                        content=content,
                                        url=post_url,
                                        metadata={
                                            "gallery":      gid,
                                            "gallery_name": label,
                                            "category":     category,
                                            "keyword":      label,
                                            "page":         page,
                                        }
                                    ))
                                    gallery_items += 1
                            except Exception as e:
                                print(f"  게시물 오류: {e}")

                    except Exception as e:
                        print(f"  페이지 {page} 오류: {e}")

                print(f"  [DC/{gid}] {gallery_items}개 수집 완료")

        finally:
            if driver:
                driver.quit()

        return items

    def _get_post_content(self, driver) -> str:
        """현재 페이지 본문 추출"""
        try:
            for sel in [".write_div", "div.writing_view_box", "div#container .view_content_wrap"]:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, sel)
                    text = elem.text.strip()
                    if text:
                        return text
                except Exception:
                    continue
        except Exception:
            pass
        return None
