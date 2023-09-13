from asyncio import AbstractEventLoop, get_event_loop
from io import BytesIO

from discord import File
from easy_pil import Editor, Font, Text

from lib.db.db_classes import LevelingStats
from lib.leveling.calculation import xp_to_level
from lib.utils import shortened


def _get_stats_text(stats: LevelingStats, font: Font) -> list[Text]:
    """
    Generates the row text for the given stats.
    :param stats: The stats to generate the row text for.
    :return: The row text.
    """

    return [
        Text(
            text="Total ",
            color=(255, 255, 255),
            font=font
        ),
        Text(
            text=f"{shortened(stats.experience)}",
            color=(238, 136, 17),
            font=font
        ),
        Text(
            text="XP",
            color=(255, 255, 255),
            font=font
        ),
        Text(
            text="Level",
            color=(255, 255, 255),
            font=font
        ),
        Text(
            text=f"{xp_to_level(stats.experience)[1]}",
            color=(238, 136, 17),
            font=font
        )
    ]


def _gen_leaderboard(
        stats: list[LevelingStats],
        avatars: list[bytes],
        user_names: list[str],
        guild_name: str,
        page: int
) -> list[File]:
    """
    Generates a leaderboard image.

    :param stats: The stats to generate a leaderboard for.
    :param avatars: The avatars of the users.
    :param user_names: The names of the users.
    :param guild_name: The name of the guild.
    :param page: The page to generate a leaderboard for.
    :return: The leaderboard as a list of :class:`discord.File`.
    """

    roboto25_it: Font = Font("./assets/fonts/Roboto/Roboto-Italic.ttf", 25)
    roboto27: Font = Font("./assets/fonts/Roboto/Roboto-Regular.ttf", 27)

    editor: Editor = Editor("./assets/leaderboard.png")
    editor.text(
        text=guild_name,
        position=(25, 75),
        font=roboto25_it,
        color=(255, 255, 255)
    )
    editor.text(
        text=f"Page {page}",
        position=(925, 25),
        font=roboto25_it,
        color=(255, 255, 255),
        align="right"
    )

    for i, info in enumerate(zip(stats[:8], avatars[:8], user_names[:8]), start=1 + (page - 1) * 8):
        stat, avatar, username = info

        editor.paste(
            Editor(BytesIO(avatar)).circle_image().resize(size=(30, 30)),
            (20, 130 + i * 50)
        )
        editor.text(
            text=f"{i}. {username}",
            position=(70, 134 + i * 50),
            font=roboto27,
            color=(255, 255, 255)
        )

        stat_texts: list[Text] = _get_stats_text(stat, roboto27)
        editor.multi_text(
            texts=stat_texts[:3],
            position=(562, 145 + i * 50)
        )
        editor.multi_text(
            texts=stat_texts[3:],
            position=(796, 145 + i * 50)
        )
    page_1: File = File(editor.image_bytes, filename="leaderboard.png")

    if not len(stats) > 8:
        return [page_1]

    editor: Editor = Editor("./assets/leaderboard2.png")

    for i, info in enumerate(zip(stats[8:], avatars[8:], user_names[8:]), start=1 + (page - 1) * 8):
        stat, avatar, username = info

        editor.paste(
            Editor(BytesIO(avatar)).circle_image().resize(size=(30, 30)),
            (20, -40 + i * 50)
        )
        editor.text(
            text=f"{i + 8}. {username}",
            position=(70, -36 + i * 50),
            font=roboto27,
            color=(255, 255, 255)
        )

        stat_texts: list[Text] = _get_stats_text(stat, roboto27)
        editor.multi_text(
            texts=stat_texts[:3],
            position=(562, -25 + i * 50)
        )
        editor.multi_text(
            texts=stat_texts[3:],
            position=(796, -25 + i * 50)
        )
    return [page_1, File(editor.image_bytes, filename="leaderboard2.png")]


async def gen_leaderboard(
        stats: list[LevelingStats],
        avatars: list[bytes],
        user_names: list[str],
        guild_name: str,
        page: int,
        loop: AbstractEventLoop = None
) -> File | list[File]:
    """
    Generates a leaderboard image.

    :param stats: The stats to generate a leaderboard for.
    :param avatars: The avatars of the users.
    :param user_names: The names of the users.
    :param guild_name: The name of the guild.
    :param page: The page to generate a leaderboard for.
    :param loop: The event loop to use.
    :return: The leaderboard as a list of :class:`discord.File`.
    """

    loop = loop or get_event_loop()

    return await loop.run_in_executor(None, _gen_leaderboard, stats, avatars, user_names, guild_name, page)
