from io import BytesIO
from typing import Any

from PIL import Image
from discord import File
from easy_pil import Editor, Font, Text

from lib.experience.calculation import total_xp as collected_xp, level_size  # WHY PYTHON?!?!
from lib.experience.stats import ExperienceStats
from lib.utils.utils import shortened


async def generate_rank_card(stats: ExperienceStats) -> File:
    editor: Editor = Editor(Image.open("./assets/lvl_stats.png"))
    try:
        _avatar: bytes = await stats.member.avatar.read()
    except AttributeError:
        _avatar: bytes = await stats.member.default_avatar.read()
    avatar: Editor = Editor(Image.open(BytesIO(_avatar)).resize(size=(141, 141))).circle_image()
    editor.paste(avatar, (145, 30))

    editor.text(
        position=(225, 200),
        text=str(stats.member),
        align="center",
        color=(255, 255, 255),
        font=Font(path="./assets/font.ttf", size=28)
    )

    total_xp: list[Text] = [
        Text(
            text="Total XP",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=30)
        ),
        Text(
            text=str(shortened(collected_xp(stats.xp, stats.level))),
            font=Font(path="./assets/font.ttf", size=30),
            color=(255, 122, 0)
        )
    ]
    editor.multi_text(
        texts=total_xp,
        position=(915, 40),
        align="right"
    )

    message_amount: list[Text] = [
        Text(
            text="Messages",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=30)
        ),
        Text(
            text=str(shortened(stats.message_amount)),
            font=Font(path="./assets/font.ttf", size=30),
            color=(255, 122, 0)
        )
    ]
    editor.multi_text(
        texts=message_amount,
        position=(475, 120),
        align="left"
    )

    level: list[Text] = [
        Text(
            text="Level",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=30)
        ),
        Text(
            text=str(stats.level),
            font=Font(path="./assets/font.ttf", size=30),
            color=(255, 122, 0)
        )
    ]
    editor.multi_text(
        texts=level,
        position=(725, 120),
        align="left"
    )

    editor.text(
        position=(870, 178),
        text=f"{stats.xp} / {level_size(stats.level)} XP",
        align="right",
        color=(255, 255, 255),
        font=Font(path="./assets/font.ttf", size=22)
    )

    bar_width: int = 400
    bar_height: int = 40
    unfilled_bar: Editor = Editor(Image.new(
        mode="RGBA",
        size=(bar_width, bar_height),
        color=(65, 68, 70)
    )).rounded_corners(20)
    editor.paste(unfilled_bar, (490, 200))

    editor.bar(
        position=(490, 200),
        max_width=bar_width,
        height=bar_height,
        percentage=round((stats.xp / level_size(stats.level))*100),
        radius=20,
        color=(81, 196, 108)
    )

    path: str = f"./data/cache/rank_card{stats.member.guild.id}_{stats.member.id}.png"
    editor.save(path, format="PNG")

    with open(path, "rb") as f:
        path = path.replace("./data/cache/", "")

        f: Any = f
        picture = File(f, filename=path)
    return picture
