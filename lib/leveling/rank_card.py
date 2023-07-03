from asyncio import AbstractEventLoop, get_event_loop
from io import BytesIO

from PIL import Image
from discord import File, Member
from easy_pil import Editor, Font, Text

from lib.db.db_classes import LevelingStats
from lib.leveling.calculation import xp_to_level, level_size
from lib.utils import shortened

_LEVEL_SIZE = 256


def _generate_rank_card(stats: LevelingStats, avatar: bytes, username: str, rank: int, rank_global: int) -> File:
    """
    Generates a rank card for the given stats.

    :param stats: The stats to generate a rank card for.
    :param avatar: The avatar of the member to generate a rank card for.
    :param username: The username of the member to generate a rank card for.
    :param rank: The rank of the member to generate a rank card for.

    :return: The rank card as a :class:`discord.File`.
    """

    editor: Editor = Editor(
        Image.new(
            mode="RGBA",
            size=(934, 251),
            color=(48, 51, 55, 255)
        )
    )
    xp, level = xp_to_level(stats.experience)

    editor.bar(
        position=(468, 221),
        max_width=446,
        height=19,
        percentage=round((xp / level_size(level))*100),
        color=(238, 136, 17)
    )
    editor.paste(Image.open("./assets/rank_card.png"), (0, 0))

    avatar = BytesIO(avatar)
    editor.paste(
        Editor(avatar).circle_image().resize(size=(141, 141)),
        (145, 30)
    )
    del avatar

    roboto22: Font = Font("./assets/fonts/Roboto/Roboto-Regular.ttf", 22)
    roboto27: Font = Font("./assets/fonts/Roboto/Roboto-Regular.ttf", 27)
    roboto35: Font = Font("./assets/fonts/Roboto/Roboto-Regular.ttf", 35)

    editor.text(
        text=username,
        position=(225, 200),
        font=roboto27,
        color=(255, 255, 255),
        align="center"
    )
    rank_texts: list[Text] = [
        Text(
            text=f"RANK ",
            color=(163, 166, 170),
            font=roboto22
        ),
        Text(
            text=f"#",
            color=(255, 255, 255),
            font=roboto35
        ),
        Text(
            text=f"{rank}",
            color=(238, 136, 17),
            font=roboto35
        )
    ]
    editor.multi_text(
        position=(694, 100),
        texts=rank_texts,
        space_separated=False
    )

    rank_global_texts: list[Text] = [
        Text(
            text=f"GLOBAL ",
            color=(163, 166, 170),
            font=roboto22
        ),
        Text(
            text=f"#",
            color=(255, 255, 255),
            font=roboto35
        ),
        Text(
            text=f"{rank_global}",
            color=(238, 136, 17),
            font=roboto35
        )
    ]
    editor.multi_text(
        position=(694, 140),
        texts=rank_global_texts,
        space_separated=False
    )

    messages: list[Text] = [
        Text(
            text=f"{shortened(stats.message_count)}",
            color=(238, 136, 17),
            font=roboto35
        ),
        Text(
            text=f"MESSAGE{'S' if stats.message_count != 1 else ''}",
            color=(163, 166, 170),
            font=roboto22
        )
    ]
    editor.multi_text(
        position=(661, 100),
        texts=messages,
        align="right"
    )

    level_text: list[Text] = [
        Text(
            text=f"LEVEL",
            color=(163, 166, 170),
            font=roboto22
        ),
        Text(
            text=f" {level if level > 0 else '-'}",
            color=(238, 136, 17),
            font=roboto35
        )
    ]
    editor.multi_text(
        position=(475, 203),
        texts=level_text
    )

    editor.text(
        position=(910, 194),
        text=f"{shortened(xp)} / {shortened(level_size(level))} XP",
        align="right",
        color=(255, 255, 255),
        font=roboto22
    )
    return File(editor.image_bytes, filename="rank_card.png")


async def generate_rank_card(
        stats: LevelingStats,
        member: Member,
        rank: int,
        rank_global: int,
        loop: AbstractEventLoop = None
) -> File:
    """
    Generates a rank card for the given stats.

    :param stats: The stats to generate a rank card for.
    :param member: The member to generate a rank card for.
    :param rank: The rank of the member.
    :param rank_global: The global rank of the member.
    :param loop: The event loop to use.

    :return: The rank card as a :class:`discord.File`.
    """

    loop = loop or get_event_loop()

    try:
        _member_avatar: bytes = await member.avatar.read()
    except AttributeError:
        _member_avatar: bytes = await member.default_avatar.read()
    return await loop.run_in_executor(None, _generate_rank_card, stats, _member_avatar, member.name, rank, rank_global)
