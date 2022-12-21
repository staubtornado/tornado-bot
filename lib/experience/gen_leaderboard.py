from io import BytesIO
from typing import Any

from PIL import Image
from discord import File
from easy_pil import Editor, Font, Text

from lib.db.data_objects import ExperienceStats
from lib.utils.utils import shortened


def _add_row(editor: Editor, index: int, start_px: int, offset_px: int, stats: ExperienceStats) -> None:
    editor.text(
        text=f"{index}. {stats.member}",
        color=(255, 255, 255),
        font=Font(path="./assets/font.ttf", size=27),
        position=(70, start_px + offset_px * (index - (8 if index > 7 else 1)))
    )

    editor.multi_text(
        texts=[
            Text(
                text="Total XP",
                color=(255, 255, 255),
                font=Font(path="./assets/font.ttf", size=27),
            ),
            Text(
                text=str(shortened(stats.total)),
                color=(236, 246, 19),
                font=Font(path="./assets/font.ttf", size=27),
            )],
        position=(562, start_px + offset_px * (index - (8 if index > 7 else 1))),
        align="left"
    )
    editor.multi_text(
        texts=[
            Text(
                text="Level",
                color=(255, 255, 255),
                font=Font(path="./assets/font.ttf", size=27),
            ),
            Text(
                text=str(stats.level),
                color=(236, 246, 19),
                font=Font(path="./assets/font.ttf", size=27),
            )],
        position=(796, start_px + offset_px * (index - (8 if index > 7 else 1))),
        align="left"
    )


async def generate_leaderboard_card(stats: list[ExperienceStats]) -> list[File]:
    editor: Editor = Editor(Image.open("./assets/leaderboard.png"))
    editor.text(
        text=stats[0].member.guild.name,
        position=(25, 75),
        color=(255, 255, 255),
        font=Font.poppins(variant="italic", size=25)
    )

    items_per_column: int = 7
    for i, user_stats in enumerate(stats[:items_per_column], start=1):
        try:
            _avatar: bytes = await user_stats.member.avatar.read()
        except AttributeError:
            _avatar: bytes = await user_stats.member.default_avatar.read()
        avatar: Editor = Editor(Image.open(BytesIO(_avatar)).resize((30, 30))).circle_image()
        editor.paste(avatar, position=(20, 220 + 50 * (i - 1)))
        _add_row(editor, i, 225, 50, user_stats)

    editor2: Editor = Editor(Image.open("./assets/leaderboard2.png"))
    for i, user_stats in enumerate(stats[items_per_column:], start=items_per_column + 1):
        try:
            _avatar: bytes = await user_stats.member.avatar.read()
        except AttributeError:
            _avatar: bytes = await user_stats.member.default_avatar.read()
        avatar: Editor = Editor(Image.open(BytesIO(_avatar)).resize((30, 30))).circle_image()
        editor2.paste(avatar, position=(20, 15 + 50 * (i - items_per_column - 1)))
        _add_row(editor2, i, 20, 50, user_stats)

    path: str = f"./data/cache/leaderboard{stats[0].member.guild.id}.png"
    editor.save(path, format="PNG")
    with open(path, "rb") as f:
        f: Any = f
        picture = File(f, filename=path.replace("./data/cache/", ""))

    if not len(stats) > 7:
        return [picture]

    path = path.replace(".png", "2.png")
    editor2.save(path, format="PNG")
    with open(path, "rb") as f:
        f: Any = f
        picture2 = File(f, filename=path.replace("./data/cache/", ""))
    return [picture, picture2]
