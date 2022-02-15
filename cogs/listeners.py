from discord import Guild
from discord.ext.commands import Cog

from data.db.memory import database


class Listeners(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        database.cursor().execute(f"""INSERT INTO guild (GuildID) VALUES ({guild.id})""")

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        pass


def setup(bot):
    bot.add_cog(Listeners(bot))
