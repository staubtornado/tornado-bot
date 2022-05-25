from sqlite3 import Cursor

from discord import slash_command, ApplicationContext, Bot, Embed
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.economy.views import ConfirmTransaction


class Premium(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx: ApplicationContext):
        database.cursor().execute("""INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""", (ctx.guild.id, ))

    @staticmethod
    async def has_premium(ctx: ApplicationContext) -> bool:
        cur = database.cursor()
        cur.execute("""INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""", (ctx.guild.id, ))
        return bool(cur.execute("""SELECT HasPremium from guilds where GuildID = ?""", [ctx.guild_id]).fetchone()[0])

    @staticmethod
    async def has_beta(ctx: ApplicationContext) -> bool:
        cur = database.cursor()
        cur.execute("""INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""", (ctx.guild.id, ))
        return bool(cur.execute("""SELECT HasBeta from guilds where GuildID = ?""", [ctx.guild_id]).fetchone()[0])

    @slash_command()
    async def activate(self, ctx: ApplicationContext, key: str) -> None:
        """Activate premium with a premium key."""
        await ctx.defer()

        cur: Cursor = database.cursor()
        cur.execute("SELECT HasPremium from guilds where GuildID = ?", [ctx.guild.id])
        row = cur.fetchone()

        if row[0] == 1:
            await ctx.respond("❌ **You** already **have premium**.")
            return

        if cur.execute("""SELECT KeyString from keys where KeyString = ?""", [key]).fetchone() is None:
            await ctx.respond("❌ **Invalid key**.")
            return

        cur.execute("""UPDATE guilds SET HasPremium = 1 WHERE GuildID = ?""", (ctx.guild_id, ))
        cur.execute("""DELETE from keys where KeyString = ?""", [key])

        await ctx.respond(f"🌟 **Thanks for buying** TornadoBot **Premium**! **{ctx.guild.name} has** now all "
                          f"**premium benefits**!")

    @slash_command()
    async def beta(self, ctx: ApplicationContext, key: str) -> None:
        """Deactivate or activate beta features on this server."""
        await ctx.defer(ephemeral=True)

        cur: Cursor = database.cursor()
        cur.execute("SELECT HasBeta from guilds where GuildID = ?", [ctx.guild.id])
        row = cur.fetchone()

        if row[0] == 1:
            await ctx.respond("❌ **You** already **have beta features enabled**.")
            return

        if cur.execute("""SELECT KeyString from keys where KeyString = ?""", [key]).fetchone() is None:
            await ctx.respond("❌ **Invalid key**.")
            return

        view = ConfirmTransaction()
        await ctx.respond(embed=Embed(title="Are you sure?",
                                      description="Beta features might not work as expected or lack with content. This "
                                                  "process cannot currently be reverted.",
                                      colour=SETTINGS["Colours"]["Error"]), view=view, ephemeral=True)
        await view.wait()
        if view.value:
            cur.execute("""UPDATE guilds SET HasBeta = 1 WHERE GuildID = ?""", (ctx.guild_id, ))
            cur.execute("""DELETE from keys where KeyString = ?""", [key])
            await ctx.respond(f"🐞 **Beta features** are now **enabled on** this **server**.")


def setup(bot: Bot):
    bot.add_cog(Premium(bot))
