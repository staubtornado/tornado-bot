from discord import Bot, Activity, ActivityType
from discord.ext.tasks import loop


@loop(minutes=30)
async def update_rich_presence(bot: Bot):
    await bot.wait_until_ready()

    await bot.change_presence(activity=Activity(type=ActivityType.playing, name="Closed BETA..."))
