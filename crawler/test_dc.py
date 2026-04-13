from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time, json

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')

result = {}
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    driver.get('https://gall.dcinside.com/board/lists/?id=love&page=1')
    time.sleep(4)
    result['title'] = driver.title
    posts = driver.find_elements(By.CSS_SELECTOR, 'tr.ub-content .gall_tit a:first-child')
    result['posts'] = len(posts)
    if posts:
        result['url'] = posts[0].get_attribute('href')
    driver.quit()
except Exception as e:
    result['error'] = str(e)[:200]

with open('dc_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False)
print('Done')
