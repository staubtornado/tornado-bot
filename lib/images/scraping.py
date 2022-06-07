from time import sleep
from typing import AnyStr
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options

from lib.utils.utils import url_is_valid

# DEPRECATED


class ImageScraping:
    def __init__(self, url: str):
        self.url = url

    def get_all_images(self) -> list:
        options: Options = Options()
        options.headless = True
        options.add_argument("user-agent=fake-useragent")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        try:
            driver: Chrome = Chrome(executable_path="./chromedriver.exe", chrome_options=options)
        except WebDriverException or FileNotFoundError:
            driver: Chrome = Chrome(executable_path="/usr/lib/chromium-browser/chromedriver", chrome_options=options)
        driver.get(self.url)
        for i in range(10):
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            sleep(0.3)
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

            if url_is_valid(img_url):
                if not any(x in img_url for x in ["static.pornpics.de"]):
                    if "https://gifsex.blog/gif2png.php" in img_url:
                        img_url = urljoin(self.url, img.attrs.get("data-srcgif"))
                    urls.append(img_url)
        return urls
