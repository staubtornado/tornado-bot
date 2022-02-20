from discord import slash_command, ApplicationContext
from discord.ext.commands import Cog


class Experience(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command()
    async def leaderboard(self, ctx: ApplicationContext):
        pass

    @slash_command()
    async def rank(self, ctx: ApplicationContext):
        pass


def setup(bot):
    bot.add_cog(Experience(bot))
