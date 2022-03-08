from sqlite3 import Cursor

from discord import Guild, Member, Message
from discord.ext.commands import Cog

from cogs.experience import ExperienceSystem
from data.db.memory import database


class Listeners(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        database.cursor().execute(f"""INSERT INTO guild (GuildID) VALUES ({guild.id})""")
        database.commit()

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        cur: Cursor = database.cursor()
        cur.execute(f"""DELETE from guild where GuildID = {guild.id}""")
        cur.execute(f"""DELETE from experience where GuildID = {guild.id}""")
        database.commit()

    @Cog.listener()
    async def on_member_join(self, member: Member):
        database.cursor().execute(
            f"""INSERT INTO experience (GuildID, UserID) VALUES ({member.guild.id}, {member.id})"""
        )
        database.commit()

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        database.cursor().execute(
            f"""DELETE from experience where GuildID = {member.guild.id} and UserID = {member.id}""")
        database.commit()

    @Cog.listener()
    async def on_message(self, message: Message):
        await ExperienceSystem(self.bot, message).start()


def setup(bot):
    bot.add_cog(Listeners(bot))
