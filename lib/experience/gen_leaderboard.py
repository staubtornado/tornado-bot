from io import BytesIO
from typing import Any

from PIL import Image
from discord import File
from easy_pil import Editor, Font, Text

from lib.experience.level_size import level_size
from lib.experience.stats import ExperienceStats
from lib.utils.utils import shortened


def _get_texts(stats: ExperienceStats) -> list[Text]:
    return [
        Text(
            text="Total XP",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=27),
        ),
        Text(
            text=str(shortened((level_size(stats.level - 1) if stats.level > 0 else 0) + stats.xp)),
            color=(233, 11, 255),
            font=Font(path="./assets/font.ttf", size=27),
        ),
        Text(
            text="      Level",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=27),
        ),
        Text(
            text=str(stats.level),
            color=(233, 11, 255),
            font=Font(path="./assets/font.ttf", size=27),
        )
    ]


async def generate_leaderboard_card(stats: list[ExperienceStats]) -> list[File]:
    editor: Editor = Editor(Image.open("./assets/leaderboard.png"))

    try:
        guild_icon: bytes = await stats[0].member.guild.icon.read()
    except AttributeError:
        pass
    else:
        icon: Editor = Editor(Image.open(BytesIO(guild_icon)).resize((44, 44))).circle_image()
        editor.paste(icon, (11, 60))
    editor.text(
        text=stats[0].member.guild.name,
        position=(70, 70),
        color=(255, 255, 255),
        font=Font(path="./assets/font.ttf", size=30)
    )

    items_per_column: int = 7
    offset: int = 0
    for i, user_stats in enumerate(stats[:items_per_column], start=1):
        try:
            _avatar: bytes = await user_stats.member.avatar.read()
        except AttributeError:
            _avatar: bytes = await user_stats.member.default_avatar.read()
        avatar: Editor = Editor(Image.open(BytesIO(_avatar)).resize((30, 30))).circle_image()
        editor.paste(avatar, position=(20, 220 + offset))

        editor.text(
            text=f"{i}. {user_stats.member}",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=27),
            position=(70, 225 + offset)
        )

        editor.multi_text(
            texts=_get_texts(user_stats),
            position=(875, 225 + offset),
            align="right"
        )

        editor.text(
            text=f"{i}. {user_stats.member}",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=27),
            position=(70, 225 + offset)
        )
        offset += 50

    offset = 0
    editor2: Editor = Editor(Image.open("./assets/leaderboard2.png"))
    for i, user_stats in enumerate(stats[items_per_column:], start=items_per_column + 1):
        try:
            _avatar: bytes = await user_stats.member.avatar.read()
        except AttributeError:
            _avatar: bytes = await user_stats.member.default_avatar.read()
        avatar: Editor = Editor(Image.open(BytesIO(_avatar)).resize((30, 30))).circle_image()
        editor2.paste(avatar, position=(20, 20 + offset))

        editor2.multi_text(
            texts=_get_texts(user_stats),
            position=(875, 20 + offset),
            align="right"
        )

        editor2.text(
            text=f"{i}. {user_stats.member}",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=27),
            position=(70, 20 + offset)
        )
        offset += 50

    path: str = f"./data/cache/leaderboard{stats[0].member.guild.id}_{stats[0].member.id}.png"
    editor.save(path, format="PNG")
    with open(path, "rb") as f:
        path = path.replace("./data/cache/", "")

        f: Any = f
        picture = File(f, filename=path)

    if not len(stats) > 7:
        return [picture]

    path = path.replace(".png", "2.png")
    editor2.save(path, format="PNG")
    with open(path, "rb") as f:
        path = path.replace("./data/cache/", "")

        f: Any = f
        picture2 = File(f, filename=path)
    return [picture, picture2]
