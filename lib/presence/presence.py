from discord import Bot, Activity, ActivityType
from discord.ext.tasks import loop

from data.config.settings import SETTINGS
from lib.utils.utils import shortened


@loop(seconds=SETTINGS["ServiceSyncInSeconds"])
async def update_rich_presence(bot: Bot):
    await bot.wait_until_ready()
    stats: str = f"{shortened(len(bot.guilds), precision=1)} servers | " \
                 f"{shortened(len(list(bot.get_all_members())), precision=1)} users"
    await bot.change_presence(activity=Activity(type=ActivityType.playing, name=SETTINGS['Version'] + f" | {stats}"))
