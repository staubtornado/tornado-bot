from asyncio import AbstractEventLoop, get_event_loop
from io import BytesIO

from discord import File
from easy_pil import Editor, Font, Text

from lib.db.db_classes import LevelingStats
from lib.leveling.calculation import xp_to_level


def _generate_level_up_card(stats: LevelingStats, avatar: bytes, username: str) -> File:
    """
    Generates a level up card for the given stats.

    :param stats: The stats to generate a level up card for.
    :param avatar: The avatar of the member to generate a level up card for.
    :param username: The username of the member to generate a level up card for.

    :return: The level up card as a :class:`discord.File`.
    """

    roboto33: Font = Font("./assets/fonts/Roboto/Roboto-Regular.ttf", 33)

    editor = Editor("./assets/level_up_card.png")
    editor.paste(Editor(BytesIO(avatar)).circle_image().resize(size=(141, 141)), (105, 105))

    editor.text(
        text=f"GG {username}!",
        position=(350, 125),
        font=roboto33,
        color=(255, 255, 255)
    )

    details: list[Text] = [
        Text(
            text=f"You just leveled up to level",
            font=roboto33,
            color=(255, 255, 255)
        ),
        Text(
            text=f"{xp_to_level(stats.experience)[1]}",
            font=roboto33,
            color=(238, 136, 17)
        ),
        Text(
            text=f"!",
            font=roboto33,
            color=(255, 255, 255)
        )
    ]

    editor.multi_text(
        texts=details,
        position=(350, 200),
    )
    return File(editor.image_bytes, filename="level_up_card.png")


async def generate_level_up_card(
        stats: LevelingStats,
        avatar: bytes,
        username: str,
        loop: AbstractEventLoop = None
) -> File:
    """
    Generates a level up card for the given stats.

    :param stats: The stats to generate a level up card for.
    :param avatar: The avatar of the member to generate a level up card for.
    :param username: The username of the member to generate a level up card for.
    :param loop: The event loop to use for generating the level up card.

    :return: The level-up card as a :class:`discord.File`.
    """
    loop = loop or get_event_loop()

    return await loop.run_in_executor(None, _generate_level_up_card, stats, avatar, username)
