from asyncio import sleep
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from selenium.webdriver import Chrome
from tqdm import tqdm


class ImageSystem:
    def __init__(self, url: str):
        self.url = url

    @classmethod
    def is_valid(cls, url: str):
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)

    async def get_all_images(self):
        driver = Chrome(executable_path="./chromedriver.exe")
        driver.get(self.url)
        driver.execute_script("window.scrollTo(0, 2000)")
        await sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        urls: list = []
        for img in tqdm(soup.find_all("img", recursive=True), "Extracting images"):
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