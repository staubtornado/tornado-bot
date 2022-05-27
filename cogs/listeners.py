from sqlite3 import Cursor

from discord import Guild, Member, Message, Embed
from discord.ext.commands import Cog

from cogs.experience import ExperienceSystem
from data.config.settings import SETTINGS
from data.db.memory import database


class Listeners(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        database.cursor().execute("""INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""", [guild.id])
        database.commit()
        await guild.owner.send(embed=Embed(title="Welcome!", description=f"Thanks for adding TornadoBot to "
                                                                         f"`{guild.name}`.",
                                           colour=SETTINGS["Colours"]["Default"]))

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        cur: Cursor = database.cursor()
        cur.execute("""DELETE FROM experience WHERE GuildID = ?""", (guild.id, ))
        cur.execute("""DELETE FROM settings WHERE GuildID = ?""", (guild.id, ))
        cur.execute("""DELETE FROM subjects WHERE GuildID = ?""", (guild.id,))
        database.commit()

    @Cog.listener()
    async def on_member_join(self, member: Member):
        pass

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        database.cursor().execute("""DELETE from experience where GuildID = ? and UserID = ?""",
                                  (member.guild.id, member.id))
        database.commit()

    @Cog.listener()
    async def on_message(self, message: Message):
        await ExperienceSystem(self.bot, message).start()


def setup(bot):
    bot.add_cog(Listeners(bot))
