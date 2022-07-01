from PIL import Image
from discord import File


def ping(url: str) -> tuple[str, File]:
    icon: Image = Image.open(url)
    asset: Image = Image.open("./assets/ping.png").resize((int(icon.size[0] * 0.90), int(icon.size[1] * 0.90)))

    icon.paste(asset, (icon.size[0] - asset.size[0], icon.size[1] - asset.size[1]), asset)
    icon.save(url, "PNG")
    return f"attachment://{url.split('/')[-1]}", File(url)

