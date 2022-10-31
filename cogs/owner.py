from discord import Bot, slash_command, ApplicationContext, Embed, Forbidden, Activity, ActivityType, Status
from discord.ext.commands import Cog

from data.config.settings import SETTINGS


class Owner(Cog):
    """Commands limited to the bot owners."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.public = False

    @slash_command(guild_ids=SETTINGS["OwnerGuilds"])
    async def maintenance(self, ctx: ApplicationContext, datetime: str, reason: str, duration: int) -> None:
        """Schedule and announce a maintenance."""

        await ctx.defer()
        embed: Embed = Embed(
            title="Maintenance scheduled.",
            description="You may experience downtime or unexpected behavior while using our services. This is required "
                        "to maintain them.",
            color=SETTINGS["Colours"]["Default"]
        )
        embed.add_field(name="Datetime", value=datetime)
        embed.add_field(name="Duration", value=f"{duration} minutes")
        embed.add_field(name="Reason", value=reason, inline=False)

        await self.bot.change_presence(
            activity=Activity(type=ActivityType.listening, name="Maintenance!"),
            status=Status.dnd
        )

        for guild in self.bot.guilds:
            try:
                await guild.owner.send(embed=embed)
            except Forbidden:
                continue
        await ctx.respond(f"📨 **Contacted {len(self.bot.guilds)}** guild **owners**.")


def setup(bot: Bot) -> None:
    bot.add_cog(Owner(bot))
