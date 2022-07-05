from PIL import Image
from discord import File


def ping(url: str) -> tuple[str, File]:
    icon: Image = Image.open(url)

    output: Image = Image.new("RGBA", icon.size)
    position: tuple[int, int] = (int((output.size[0] - icon.size[0] * 0.95) / 2),
                                 int((output.size[1] - icon.size[1] * 0.95) / 2))
    output.paste(icon.resize((int(icon.size[0] * 0.95), int(icon.size[1] * 0.95))), position)

    asset: Image = Image.open("./assets/ping.png").resize((int(icon.size[0] * 0.95), int(icon.size[1] * 0.95)))
    output.paste(asset, position, asset)
    output.save(url, "PNG")
    return f"attachment://{url.split('/')[-1]}", File(url)
