from sqlite3 import Cursor

from discord import Guild, Member, Message
from discord.ext.commands import Cog

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
        database.cursor().execute(f"""DELETE from guild where GuildID = {guild.id}""")
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
        cur: Cursor = database.cursor()

        select_query: str = f"""SELECT Messages from experience where (GuildID, UserID) = ({message.guild.id}, 
        {message.author.id})"""

        cur.execute(select_query)
        messages: int = cur.fetchone()

        if messages is None:
            cur.execute(
                f"""INSERT INTO experience (GuildID, UserID) VALUES ({message.guild.id}, {message.author.id})""")
        cur.execute(f"""UPDATE experience SET Messages = Messages + 1 
                        WHERE (GuildID, UserID) = ({message.guild.id}, {message.author.id})""")


def setup(bot):
    bot.add_cog(Listeners(bot))
