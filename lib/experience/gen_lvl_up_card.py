from io import BytesIO

from discord import File
from easy_pil import Editor, Font, Text

from lib.db.data_objects import ExperienceStats
from lib.utils.utils import read_file


async def generate_lvl_up_card(stats: ExperienceStats) -> File:
    editor: Editor = Editor(BytesIO(await read_file("./assets/lvl_up_card.png")))

    try:
        _avatar: bytes = await stats.member.avatar.read()
    except AttributeError:
        _avatar: bytes = await stats.member.default_avatar.read()
    avatar: Editor = Editor(BytesIO(_avatar)).circle_image().resize(size=(141, 141))
    editor.paste(avatar, (105, 105))
    del _avatar, avatar

    editor.text(
        position=(350, 125),
        text=f"GG {stats.member},",
        font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35),
        color=(255, 255, 255)
    )

    texts: list[Text] = [
        Text(
            text="you are now level",
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35),
            color=(255, 255, 255)
        ),
        Text(
            text=str(stats.level),
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35),
            color=(0, 255, 255)
        ),
        Text(
            text=f"on this server.",
            font=Font(path="./assets/fonts/Roboto-Regular.ttf", size=35),
            color=(255, 255, 255)
        )
    ]
    editor.multi_text(position=(350, 200), texts=texts)
    return File(editor.image_bytes, filename="lvl_up_card.png")
