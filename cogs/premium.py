from sqlite3 import Cursor
from time import sleep

from discord import slash_command, ApplicationContext
from discord.ext.commands import Cog

from data.db.memory import database

premium_guilds: list = []
beta_guilds: list = []


def update_guilds():
    premium_guilds.clear()
    beta_guilds.clear()
    sleep(5)
    query: str = """SELECT * from guilds where HasPremium = 1 OR HasBeta = 1"""
    sleep(5)
    for row in database.cursor().execute(query):
        print(row)


class Premium(Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def has_premium(guild_id: int) -> bool:
        return bool(database.cursor().execute("""SELECT HasPremium from guilds where GuildID = ?""", [guild_id]))

    @staticmethod
    async def has_beta(guild_id: int) -> bool:
        return bool(database.cursor().execute("""SELECT HasBeta from guilds where GuildID = ?""", [guild_id]))

    @slash_command()
    async def activate(self, ctx: ApplicationContext, key: str) -> None:
        database.cursor().execute("""Update guilds set HasPremium = 1 where GuildID = ?""", [ctx.guild.id])
        database.commit()
        await ctx.respond(f"🌟 **Thanks for buying** TornadoBot **Premium**! **{ctx.guild.name} has** now all "
                          f"**premium benefits**!")

    @slash_command()
    async def beta(self, ctx: ApplicationContext, state: bool, *, key: str = None) -> None:
        cur: Cursor = database.cursor()
        cur.execute("SELECT HasBeta from guilds where GuildID = ?", [ctx.guild.id])

        def update_db():
            row = cur.fetchone()

            if row is None:
                if key is None:
                    await ctx.respond("It is your first time switching to our beta. Please enter your beta key.")
                    return
                cur.execute("""INSERT INTO guilds (GuildID, HasBeta) VALUES (?, ?)""", [ctx.guild.id, int(state)])
                return
            cur.execute("""Update guilds set HasBeta = ? where GuildID = ?""", (int(state), ctx.guild.id))

        update_db()
        database.commit()

        if state:
            state: str = "available on this server**, some of them **might cause bugs**. Thanks for your patience."
        else:
            state: str = "disabled** on this server."
        await ctx.respond(f"✅ **Beta features are now {state}")


def setup(bot):
    bot.add_cog(Premium(bot))
