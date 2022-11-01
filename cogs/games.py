from discord import Bot, slash_command, Member
from discord.ext.commands import Cog


class Games(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command()
    async def tictactoe(self, enemy: Member):

        pass


def setup(bot: Bot):
    bot.add_cog(Games(bot))
