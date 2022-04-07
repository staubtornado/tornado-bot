from time import sleep
from typing import AnyStr
from urllib.parse import urlparse, urljoin, ParseResult

from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options


class ImageSystem:
    def __init__(self, url: str):
        self.url = url

    @classmethod
    def is_valid(cls, url: str) -> bool:
        parsed: ParseResult = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)

    def get_all_images(self) -> list:
        options: Options = Options()
        options.headless = True
        options.add_argument('user-agent=fake-useragent')

        try:
            driver: Chrome = Chrome(executable_path="./chromedriver.exe", chrome_options=options)
        except WebDriverException or FileNotFoundError:
            driver: Chrome = Chrome(executable_path="/usr/lib/chromium-browser/chromedriver", chrome_options=options)
        driver.get(self.url)
        for i in range(10):
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            sleep(0.5)
        soup: BeautifulSoup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        urls: list = []
        for img in soup.find_all("img", recursive=True):
            img_url = img.attrs.get("src")
            if not img_url:
                continue
            img_url: AnyStr = urljoin(self.url, img_url)

            try:
                pos: int = img_url.index("?")
                img_url = img_url[:pos]
            except ValueError:
                pass

            if self.is_valid(img_url):
                if "static.pornpics.de" not in img_url:
                    urls.append(img_url)
        return urls
