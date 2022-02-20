from discord import slash_command, ApplicationContext
from discord.ext.commands import Cog
from discord.commands import Option

from data.db.memory import database


class Premium(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command()
    async def activate(self, ctx: ApplicationContext, key: str) -> None:
        database.cursor().execute(f"""Update guild set HasPremium = 1 where GuildID = {ctx.guild.id}""")
        database.commit()
        await ctx.respond(f"🌟 **Thanks for buying** TornadoBot **Premium**! **{ctx.guild.name} has** now all "
                          f"**premium benefits**!")

    @slash_command()
    async def beta(self, ctx: ApplicationContext, state: bool, key: Option(str, "Your closed beta access key.",
                                                                           required=False)):
        database.cursor().execute(f"""Update guild set HasBeta = {int(state)} where GuildID = {ctx.guild.id}""")
        database.commit()
        await ctx.respond("✅ **Beta features are now available on this server**, some of them **might cause bugs**. "
                          "Thanks for your patience.")


def setup(bot):
    bot.add_cog(Premium(bot))
