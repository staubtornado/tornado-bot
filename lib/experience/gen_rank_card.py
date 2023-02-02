from io import BytesIO

from PIL import Image
from discord import File
from easy_pil import Editor, Font, Text

from lib.db.data_objects import ExperienceStats
from lib.experience.calculation import level_size  # WHY PYTHON?!?!
from lib.utils.utils import shortened, read_file


async def generate_rank_card(stats: ExperienceStats) -> File:
    editor: Editor = Editor(Image.new(
        mode="RGBA",
        size=(934, 251),
        color=(48, 51, 55, 255)
    ))
    editor.bar(
        position=(468, 221),
        max_width=446,
        height=19,
        percentage=round((stats.xp / level_size(stats.level))*100),
        color=(238, 136, 17)
    )
    editor.paste(
        Editor(BytesIO(await read_file("./assets/lvl_stats.png"))),
        (0, 0)
    )

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
        font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=28)
    )

    rank: list[Text] = [
        Text(
            text=f"RANK ",
            color=(163, 166, 170),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=22)
        ),
        Text(
            text=f"#",
            color=(255, 255, 255),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35)
        ),
        Text(
            text=f"{stats.rank}",
            color=(238, 136, 17),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35)
        )
    ]
    editor.multi_text(
        position=(694, 100),
        texts=rank,
        space_separated=False
    )

    _percentile: float = (stats.rank / stats.member.guild.member_count) * 100
    if _percentile <= 0.01:
        percentile: tuple[str, str] = "TOP ", "  0.01"
    elif _percentile <= 50:
        percentile: tuple[str, str] = "TOP ", f"  {(round(_percentile, 2))}"
    else:
        percentile: tuple[str, str] = "BOTTOM ", f" {round(100 - _percentile, 2)}"
    del _percentile

    percentile: list[Text] = [
        Text(
            text=f"{percentile[0]}",
            color=(163, 166, 170),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=22)
        ),
        Text(
            text=f"{percentile[1]}",
            color=(238, 136, 17),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35)
        ),
        Text(
            text=f"%",
            color=(255, 255, 255),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35)
        )
    ]
    editor.multi_text(
        position=(694, 140),
        texts=percentile,
        space_separated=False
    )

    messages: list[Text] = [
        Text(
            text=f"{shortened(stats.message_amount)}",
            color=(238, 136, 17),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35),
        ),
        Text(
            text=f"MESSAGE{'S' if stats.message_amount != 1 else ''}",
            color=(163, 166, 170),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=22),
        )
    ]
    editor.multi_text(
        position=(661, 100),
        texts=messages,
        align="right"
    )

    level: list[Text] = [
        Text(
            text=f"LEVEL",
            color=(163, 166, 170),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=22),
        ),
        Text(
            text=f" {stats.level if stats.level > 0 else '-'}",
            color=(238, 136, 17),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35),
        )
    ]
    editor.multi_text(
        position=(475, 203),
        texts=level
    )

    editor.text(
        position=(910, 194),
        text=f"{shortened(stats.xp)} / {shortened(level_size(stats.level))} XP",
        align="right",
        color=(255, 255, 255),
        font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=22)
    )
    return File(editor.image_bytes, filename="rank_card.png")
