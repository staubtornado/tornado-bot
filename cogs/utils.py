from discord import Bot, slash_command, ApplicationContext, Member, AutocompleteContext, Option, Embed, Forbidden
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from lib.utils.utils import extract_int


async def get_reasons(ctx: AutocompleteContext) -> list:
    return ["Violation of Rules", "Spam", "Harassment", "Advertisement", "NSFW outside of the NSFW channels",
            "Violation of Discord Community Guidelines or Terms of Service.", "Inappropriate name or profile picture"]


async def get_banned_members(ctx: AutocompleteContext) -> list:
    rtrn = []
    for entry in await ctx.interaction.guild.bans():
        option = f"{str(entry.user).replace('|', '')} ( {entry.user.id} ) | Reason: {entry.reason}"
        if len(option) > 100:
            option = f"{option[:97]}..."
        rtrn.append(option)
    return rtrn


class Utilities(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command()
    async def purge(self, ctx: ApplicationContext, amount: int = 100, ignore: Member = None,
                    oldest_first: bool = False):
        """Deletes latest 100 messages in this channel by default. Can be increased up to 1000."""

        def is_ignored(m) -> bool:
            return m.author == ignore
        await ctx.channel.purge(limit=amount, check=is_ignored, oldest_first=oldest_first)

    @slash_command()
    async def ban(self, ctx: ApplicationContext, user: Member,
                  reason: Option(str, "Select a preset or enter a reason.", autocomplete=get_reasons,
                                 required=False) = "None"):
        """Bans a user from the guild."""
        await ctx.defer()

        embed = Embed(title="You got banned.", description=f"You got banned on `{ctx.guild.name}`.",
                      colour=SETTINGS["Colours"]["Error"])
        embed.add_field(name="Reason", value=reason)

        state = ""
        try:
            await user.send(embed=embed)
        except Forbidden:
            state = "\n❌  Failed to notify him."
        await ctx.guild.ban(user=user, reason=reason)
        await ctx.respond(f"🔨 **Banned {user}**.{state}")

    @slash_command()
    async def unban(self, ctx: ApplicationContext,
                    user: Option(str, "Select a banned user.", autocomplete=get_banned_members, required=True),
                    reason: str = None):
        """Unbans a user from the guild."""
        await ctx.defer()

        ints = extract_int(str(user).split("|")[0])
        ints = ints[len(ints) - 1]
        member = self.bot.get_user(ints)

        await ctx.guild.unban(member, reason=reason)
        await ctx.respond(f"**Unbanned {member}**.")


def setup(bot: Bot):
    bot.add_cog(Utilities(bot))
