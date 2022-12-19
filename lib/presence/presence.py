from discord import Activity, ActivityType
from discord.ext.tasks import loop

from bot import CustomBot
from data.config.settings import SETTINGS
from lib.utils.utils import shortened


@loop(seconds=SETTINGS["ServiceSyncInSeconds"])
async def update_rich_presence(bot: CustomBot) -> None:
    await bot.wait_until_ready()
    try:
        bot.latencies.append(round(bot.latency * 1000))
    except AttributeError:
        pass

    stats: str = (
        f"{shortened(len(bot.guilds), precision=1)} Guilds | "
        f"{shortened(len(list(bot.get_all_members())), precision=1)} Users"
    )
    await bot.change_presence(activity=Activity(type=ActivityType.playing, name=SETTINGS['Version'] + f" | {stats}"))
