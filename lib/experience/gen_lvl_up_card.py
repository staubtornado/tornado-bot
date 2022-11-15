from io import BytesIO
from typing import Any

from PIL import Image
from discord import File
from easy_pil import Editor, Font, Text

from lib.experience.stats import ExperienceStats


async def generate_lvl_up_card(stats: ExperienceStats) -> File:
    editor: Editor = Editor(Image.open("./assets/lvl_up_card.png"))
    try:
        _avatar: bytes = await stats.member.avatar.read()
    except AttributeError:
        _avatar: bytes = await stats.member.default_avatar.read()
    avatar: Editor = Editor(Image.open(BytesIO(_avatar)).resize(size=(141, 141))).circle_image()
    editor.paste(avatar, (105, 105))

    editor.text(
        position=(350, 125),
        text=f"GG {stats.member},",
        font=Font(path="./assets/font.ttf", size=35),
        color=(255, 255, 255)
    )

    texts: list[Text] = [
        Text(
            text="you are now level",
            font=Font(path="./assets/font.ttf", size=35),
            color=(255, 255, 255)
        ),
        Text(
            text=str(stats.level),
            font=Font(path="./assets/font.ttf", size=35),
            color=(0, 255, 255)
        ),
        Text(
            text=f"on this server.",
            font=Font(path="./assets/font.ttf", size=35),
            color=(255, 255, 255)
        )
    ]
    editor.multi_text(position=(350, 200), texts=texts)

    path: str = f"./data/cache/lvl_up{stats.member.guild.id}_{stats.member.id}.png"
    editor.save(path, format="PNG")

    with open(path, "rb") as f:
        path = path.replace("./data/cache/", "")

        f: Any = f
        picture = File(f, filename=path)
    return picture
