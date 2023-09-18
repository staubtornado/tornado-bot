from discord import ApplicationContext, slash_command
from discord.ext.commands import Cog

from lib.music.audio_player import AudioPlayer
from lib.music.extraction import YTDLSource
from lib.music.song import Song


class Test(Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @slash_command(name="test", description="Test command")
    async def test(self, ctx: ApplicationContext) -> None:
        pass


def setup(bot):
    bot.add_cog(Test(bot))
