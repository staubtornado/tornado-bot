from asyncio import AbstractEventLoop, get_event_loop
from io import BytesIO

from discord import File, User, Member
from easy_pil import Editor, Font, Text

from lib.db.db_classes import UserStats


def _generate_stats_card(
        username: str,
        avatar: bytes,
        commands_used: int,
        music_seconds_played: int,
        songs_played: int
) -> File:
    """
    Generates a stat card.

    :param username: The username of the user.
    :param avatar: The avatar of the user.
    :param commands_used: The number of commands used.
    :param music_seconds_played: The number of seconds the user has listened to music.
    :param songs_played: The number of songs the user has played.
    :return: :class:`discord.File` The stat card.
    """

    editor: Editor = Editor('assets/stats.png')
    editor.text(
        position=(165, 200),
        text=username,
        font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
        color='#ffffff',
        align='center'
    )
    editor.paste(
        position=(100, 50),
        image=Editor(BytesIO(avatar)).circle_image().resize((120, 120))
    )
    editor.multi_text(
        texts=[
            Text(
                text=str(commands_used),
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#ff3d87'
            ),
            Text(
                text="commands used",
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#ffffff'
            ),
        ],
        position=(450, 120),
    )

    hours = music_seconds_played // 3600
    minutes = (music_seconds_played % 3600) // 60
    editor.multi_text(
        texts=[
            Text(
                text=f"{hours}",
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#ff3d87'
            ),
            Text(
                text="hours",
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#ffffff'
            ),
            Text(
                text="and",
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#808080'
            ),
            Text(
                text=f"{minutes}",
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#ff3d87'
            ),
            Text(
                text="minutes",
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#ffffff'
            ),
            Text(
                text="music streamed",
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#808080'
            ),
        ],
        position=(450, 170),
    )

    editor.multi_text(
        texts=[
            Text(
                text=str(songs_played),
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#ff3d87'
            ),
            Text(
                text="songs played",
                font=Font('assets/fonts/Roboto/Roboto-Regular.ttf', size=25),
                color='#ffffff'
            ),
        ],
        position=(450, 220),
    )
    return File(fp=editor.image_bytes, filename='stats.png')


async def generate_stats_card(
        user: User | Member,
        stats: UserStats,
        loop: AbstractEventLoop
) -> File:
    """
    Generates a stat card.

    :param user: The user to generate the card for.
    :param stats: The stats of the user.
    :param loop: The event loop.
    :return: :class:`discord.File` The stat card.
    """

    loop = loop or get_event_loop()

    try:
        avatar: bytes = await user.avatar.read()
    except AttributeError:
        avatar: bytes = await user.default_avatar.read()

    return await loop.run_in_executor(
        None,
        _generate_stats_card,
        user.name,
        avatar,
        stats.commands_used,
        stats.songs_minutes,
        stats.songs_played
    )
