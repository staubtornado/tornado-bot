from PIL import Image
from discord import File


def ping(url: str) -> tuple[str, File]:
    background: Image = Image.open(url)
    asset: Image = Image.open("./assets/ping.png")

    background.paste(asset, (background.size[0] - asset.size[0], background.size[1] - asset.size[1]), asset)
    background.save(url, "PNG")
    return f"attachment://{url.split('/')[-1]}", File(url)

