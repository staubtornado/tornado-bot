from discord import Bot, slash_command, ApplicationContext, Member
from discord.ext.commands import Cog


class Utilities(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command()
    async def purge(self, ctx: ApplicationContext, amount: int = 100, ignore: Member = None,
                    oldest_first: bool = False):
        """Deletes latest 100 messages in this channel by default. Can be increased up to 1000."""

        def is_ignored(m) -> bool:
            return m.author == ignore
        await ctx.channel.purge(limit=amount, check=is_ignored, oldest_first=oldest_first)


def setup(bot: Bot):
    bot.add_cog(Utilities(bot))
