from discord import slash_command, ApplicationContext
from discord.commands import Option
from discord.ext.commands import Cog

from data.db.memory import database


class Premium(Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def has_premium(guild_id: int) -> bool:
        return bool(database.cursor().execute(f"""SELECT HasPremium from guild where GuildID = {guild_id}"""))

    @staticmethod
    async def has_beta(guild_id: int) -> bool:
        return bool(database.cursor().execute(f"""SELECT HasBeta from guild where GuildID = {guild_id}"""))

    @slash_command()
    async def activate(self, ctx: ApplicationContext, key: str) -> None:
        database.cursor().execute(f"""Update guild set HasPremium = 1 where GuildID = {ctx.guild.id}""")
        database.commit()
        await ctx.respond(f"🌟 **Thanks for buying** TornadoBot **Premium**! **{ctx.guild.name} has** now all "
                          f"**premium benefits**!")

    @slash_command()
    async def beta(self, ctx: ApplicationContext, state: bool, key: Option(str, "Your closed beta access key.",
                                                                           required=False)) -> None:
        database.cursor().execute(f"""Update guild set HasBeta = {int(state)} where GuildID = {ctx.guild.id}""")
        database.commit()
        await ctx.respond("✅ **Beta features are now available on this server**, some of them **might cause bugs**. "
                          "Thanks for your patience.")


def setup(bot):
    bot.add_cog(Premium(bot))
