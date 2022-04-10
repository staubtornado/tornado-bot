from discord import Bot, Activity, ActivityType
from discord.ext.tasks import loop
from millify import millify

from data.config.settings import SETTINGS


@loop(minutes=SETTINGS["ServiceSyncInSeconds"])
async def update_rich_presence(bot: Bot):
    stats: str = f"{millify(len(bot.guilds), drop_nulls=True, precision=2)} servers | " \
                 f"{millify(len(list(bot.get_all_members())), drop_nulls=True, precision=2)}"
    await bot.wait_until_ready()
    await bot.change_presence(activity=Activity(type=ActivityType.playing, name=SETTINGS['Version'] + f" {stats}"))
