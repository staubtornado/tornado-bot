from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from requests import get
from tqdm import tqdm


class ImageSystem:
    def __init__(self, url: str):
        self.url = url

    @classmethod
    def is_valid(cls, url: str):
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)

    def get_all_images(self):
        soup = BeautifulSoup(get(self.url).content, "html.parser")

        urls = []
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
                urls.append(img_url)
        return urls
