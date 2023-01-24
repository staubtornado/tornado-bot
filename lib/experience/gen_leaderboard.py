from io import BytesIO

from discord import File, Member
from easy_pil import Editor, Font, Text

from data.config.settings import SETTINGS
from lib.db.data_objects import ExperienceStats
from lib.utils.utils import read_file, shortened


async def generate_leaderboard_cards(stats: list[ExperienceStats], page: tuple[int, int]) -> list[File]:
    """
    Generates up to two leaderboard cards.

    Parameters
    ----------
    stats : list[ExperienceStats]
        The stats of the members. The list must be sorted by the total xp. The first element is the first place. Length
        is specified in the settings of the bot.
    page : tuple[int, int]
        First element is the current page, second element is the max page.

    Returns
    -------
    list[File]
        :class:`discord.File` objects of the generated cards.
    """

    editor: Editor = Editor(BytesIO(await read_file('./assets/leaderboard.png')))
    editor.text(
        text=stats[0].member.guild.name,
        position=(25, 75),
        color=(255, 255, 255),
        font=Font('./assets/fonts/Roboto-Italic.ttf', 25)
    )
    editor.text(
        text=f'Page {page[0]} / {page[1]}',
        position=(925, 25),
        color=(255, 255, 255),
        font=Font('./assets/fonts/Roboto-Italic.ttf', 19),
        align='right'
    )

    async def _fetch_avatar(member: Member) -> bytes:
        try:
            return await member.avatar.read()
        except AttributeError:
            return await member.default_avatar.read()

    def _get_stats_for_row(s: ExperienceStats) -> list[Text]:
        return [
            Text(
                text=f'Total XP',
                color=(255, 255, 255),
                font=Font('./assets/fonts/Roboto-Regular.ttf', 27)
            ),
            Text(
                text=shortened(s.total),
                color=(236, 246, 19),
                font=Font('./assets/fonts/Roboto-Regular.ttf', 27)
            ),
            Text(
                text=f'Level',
                color=(255, 255, 255),
                font=Font('./assets/fonts/Roboto-Regular.ttf', 27)
            ),
            Text(
                text=str(s.level),
                color=(236, 246, 19),
                font=Font('./assets/fonts/Roboto-Regular.ttf', 27)
            )
        ]

    items_on_first_editor: int = 8
    items_on_each_page: int = SETTINGS['Cogs']['Experience']["Leaderboard"]["ItemsPerPage"]

    for i, stat in enumerate(stats[:items_on_first_editor]):
        editor.paste(
            image=Editor(BytesIO(await _fetch_avatar(stat.member))).resize((30, 30)).circle_image(),
            position=(20, 180 + 50 * i)
        )
        editor.text(
            text=f'{i + 1 + items_on_each_page * (page[0] - 1)}. {stat.member}',
            color=(255, 255, 255),
            position=(70, 185 + 50 * i),
            font=Font('./assets/fonts/Roboto-Regular.ttf', 27)
        )

        texts: list[Text] = _get_stats_for_row(stat)
        editor.multi_text(
            texts=texts[:2],
            position=(562, 195 + 50 * i)
        )
        editor.multi_text(
            texts=texts[2:],
            position=(796, 195 + 50 * i)
        )
    page_1: File = File(editor.image_bytes, filename='leaderboard.png')
    del editor

    if not len(stats) > items_on_first_editor:
        return [page_1]

    editor = Editor(BytesIO(await read_file('./assets/leaderboard2.png')))
    for i, stat in enumerate(stats[items_on_first_editor:]):
        editor.paste(
            image=Editor(BytesIO(await _fetch_avatar(stat.member))).resize((30, 30)).circle_image(),
            position=(20, 10 + 50 * i)
        )
        editor.text(
            text=f'{i + 1 + items_on_first_editor + items_on_each_page * (page[0] - 1)}. {stat.member}',
            color=(255, 255, 255),
            position=(70, 15 + 50 * i),
            font=Font('./assets/fonts/Roboto-Regular.ttf', 27)
        )

        texts: list[Text] = _get_stats_for_row(stat)
        editor.multi_text(
            texts=texts[:2],
            position=(562, 25 + 50 * i)
        )
        editor.multi_text(
            texts=texts[2:],
            position=(796, 25 + 50 * i)
        )

    page_2: File = File(editor.image_bytes, filename='leaderboard.png')
    del editor
    return [page_1, page_2]
