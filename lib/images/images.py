from time import sleep
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options


class ImageSystem:
    def __init__(self, url: str):
        self.url = url

    @classmethod
    def is_valid(cls, url: str):
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)

    def get_all_images(self):
        options = Options()
        options.headless = True
        options.add_argument('user-agent=fake-useragent')

        try:
            driver = Chrome(executable_path="./chromedriver.exe", chrome_options=options)
        except WebDriverException or FileNotFoundError:
            driver = Chrome(executable_path="/usr/lib/chromium-browser/chromedriver", chrome_options=options)
        driver.get(self.url)
        driver.execute_script("window.scrollTo(0, 2000)")
            sleep(0.5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        urls: list = []
        for img in soup.find_all("img", recursive=True):
            img_url = img.attrs.get("src")
            if not img_url:
                continue
            img_url = urljoin(self.url, img_url)

            try:
                pos = img_url.index("?")
                img_url = img_url[:pos]
            except ValueError:
                pass

            if self.is_valid(img_url):
                if "static.pornpics.de" not in img_url:
                    urls.append(img_url)
        return urls
