from io import BytesIO

from PIL import Image
from discord import File
from easy_pil import Editor, Font, Text

from lib.db.data_objects import ExperienceStats
from lib.experience.calculation import level_size  # WHY PYTHON?!?!
from lib.utils.utils import shortened, read_file


async def generate_rank_card(stats: ExperienceStats) -> File:
    editor: Editor = Editor(BytesIO(await read_file("./assets/lvl_stats.png")))
    try:
        _avatar: bytes = await stats.member.avatar.read()
    except AttributeError:
        _avatar: bytes = await stats.member.default_avatar.read()
    avatar: Editor = Editor(BytesIO(_avatar)).circle_image().resize(size=(141, 141))
    editor.paste(avatar, (145, 30))
    del _avatar, avatar

    editor.text(
        position=(225, 200),
        text=str(stats.member),
        align="center",
        color=(255, 255, 255),
        font=Font(path="./assets/font.ttf", size=28)
    )

    rank: list[Text] = [
        Text(
            text="#",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=38)
        ),
        Text(
            text=str(stats.rank if stats.rank else '?'),
            font=Font(path="./assets/font.ttf", size=38),
            color=(255, 122, 0)
        )
    ]

    editor.multi_text(
        texts=rank,
        position=(925, 28),
        align="right",
        space_separated=False
    )

    center_information: list[Text] = [
        Text(
            text="Messages",
            color=(255, 255, 255),
            font=Font(path="./assets/font.ttf", size=30)
        ),
        Text(
            text=str(shortened(stats.message_amount)),
            font=Font(path="./assets/font.ttf", size=30),
            color=(255, 122, 0)
        ),
        Text(
            text="      Level",
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
        texts=center_information,
        position=(670, 105),
        align="center"
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
    return File(editor.image_bytes, filename="rank_card.png")
