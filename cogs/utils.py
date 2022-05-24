from datetime import timedelta
from time import time, strftime, gmtime

from discord import Bot, slash_command, ApplicationContext, Member, AutocompleteContext, Option, Embed, Forbidden, \
    Message, default_permissions
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from lib.utils.utils import extract_int, time_to_string


async def get_reasons(ctx: AutocompleteContext) -> list:
    return ["Violation of Rules", "Spam", "Harassment", "Advertisement", "NSFW outside of the NSFW channels",
            "Violation of Discord Community Guidelines or Terms of Service.", "Inappropriate name or profile picture"]


async def get_banned_members(ctx: AutocompleteContext) -> list:
    rtrn = []
    async for entry in ctx.interaction.guild.bans():
        option = f"{str(entry.user).replace('|', '')} ( {entry.user.id} ) | Reason: {entry.reason}"
        if len(option) > 100:
            option = f"{option[:97]}..."
        rtrn.append(option)
    return rtrn


class Utilities(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command()
    @default_permissions(manage_messages=True)
    async def purge(self, ctx: ApplicationContext, amount: int = 100, ignore: Member = None,
                    order: Option(str, "Select where the bot should start deleting.",
                                  required=False, choices=["Oldest", "Newest"]) = "Newest"):
        """Deletes latest 100 messages in this channel by default. Can be increased up to 1000."""
        await ctx.defer()

        def is_ignored(m: Message) -> bool:
            return m.author == ignore
        await ctx.respond(
            f"**Deleted {len(await ctx.channel.purge(limit=amount, check=is_ignored, oldest_first=order != 'Newest'))} "
            f"messages**.", ephemeral=True)

    @slash_command()
    @default_permissions(kick_members=True)
    async def kick(self, ctx: ApplicationContext, user: Member,
                   reason: Option(str, "Select a preset or enter a reason.", autocomplete=get_reasons,
                                  required=False) = "None"):
        """Removes a user from the guild."""

        embed = Embed(title="You got kicked.", description=f"You got kicked on `{ctx.guild.name}`.",
                      colour=SETTINGS["Colours"]["Error"])
        embed.add_field(name="Reason", value=reason)

        state = ""
        try:
            await user.send(embed=embed)
        except Forbidden:
            state = "\n❌  Failed to notify him."
        await ctx.guild.kick(user=user, reason=reason)
        await ctx.respond(f"👟 **Kicked {user}**.{state}")

    @slash_command()
    @default_permissions(ban_members=True)
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
    @default_permissions(ban_members=True)
    async def unban(self, ctx: ApplicationContext,
                    user: Option(str, "Select a banned user.", autocomplete=get_banned_members, required=True),
                    reason: str = None):
        """Unbans a user from the guild."""
        await ctx.defer()

        ints = extract_int(str(user).split("|")[0])
        ints = ints[len(ints) - 1]
        member = self.bot.get_user(ints)

        await ctx.guild.unban(member, reason=reason)
        await ctx.respond(f"🤝 **Unbanned {member}**.")

    @slash_command()
    async def ping(self, ctx: ApplicationContext):
        """Check the bots ping to the Discord API."""
        await ctx.respond(f"**Ping**: `{round(self.bot.latency * 1000)}ms`")

    @slash_command()
    async def uptime(self, ctx: ApplicationContext):
        """Check the bots' uptime."""
        await ctx.respond(f"**Uptime**: {time_to_string(time() - self.bot.uptime)}")

    @slash_command()
    async def help(self, ctx: ApplicationContext):
        """Get a list of features and information about the bot."""
        embed = Embed(title="TornadoBot", colour=SETTINGS["Colours"]["Default"],
                      description="Add to server | Support Server | GitHub")
        await ctx.respond(embed=embed)


def setup(bot: Bot):
    bot.add_cog(Utilities(bot))
