from difflib import get_close_matches
from time import time

from discord import Bot, slash_command, ApplicationContext, Member, AutocompleteContext, Option, Embed, Forbidden, \
    default_permissions, SlashCommandGroup
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from lib.utils.utils import extract_int, time_to_string, get_permissions, create_graph


async def get_reasons(ctx: AutocompleteContext) -> list[str]:
    rtrn = ["Violation of Rules", "Spam", "Harassment", "Advertisement", "NSFW outside of the NSFW channels",
            "Violation of Discord Community Guidelines or Terms of Service.", "Inappropriate name or profile picture"]
    if ctx.value == "":
        return rtrn
    return [x for x in rtrn if x.lower().startswith(ctx.value.lower())]


async def get_cogs(ctx: AutocompleteContext) -> list[str]:
    rtrn = []

    for cog in ctx.bot.cogs:
        cog = ctx.bot.get_cog(cog)
        try:
            if not cog.public:
                continue
        except AttributeError:
            pass
        rtrn.append(cog.qualified_name.lower())
    if ctx.value == "":
        return rtrn
    return [x for x in rtrn if x.lower().startswith(ctx.value.lower())]


async def get_banned_members(ctx: AutocompleteContext) -> list[str]:
    rtrn = []
    async for entry in ctx.interaction.guild.bans():
        option = f"{str(entry.user).replace('|', '')} ( {entry.user.id} ) | Reason: {entry.reason}"
        if len(option) > 100:
            option = f"{option[:97]}..."
        rtrn.append(option)
    return rtrn


class Utilities(Cog):
    """
    Useful commands for moderators, server owners and information about the bot.
    """
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command()
    @default_permissions(manage_messages=True)
    async def purge(self, ctx: ApplicationContext, amount: int = 100,
                    order: Option(str, "Select where the bot should start deleting.",
                                  required=False, choices=["Oldest", "Newest"]) = "Newest"):
        """Deletes latest 100 messages in this channel by default. Can be increased up to 1000."""
        await ctx.defer()

        await ctx.respond(
            f"**Deleted {len(await ctx.channel.purge(limit=amount, oldest_first=order != 'Newest'))} "
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
        self.bot.latencies.append(round(self.bot.latency * 1000))

        image, file = create_graph(self.bot.latencies)
        await ctx.respond(f"**Ping**: `{round(self.bot.latency * 1000)}ms`", file=file)

    @slash_command()
    async def uptime(self, ctx: ApplicationContext):
        """Check the bots' uptime."""
        await ctx.respond(f"**Uptime**: {time_to_string(time() - self.bot.uptime)}")

    @slash_command()
    async def help(self, ctx: ApplicationContext,
                   extension: Option(str, description="Select an extension for which you want to receive precise "
                                                      "information.", autocomplete=get_cogs, required=False) = None):
        """Get a list of features and information about the bot."""
        embed = Embed(title="Help", colour=SETTINGS["Colours"]["Default"],
                      description=f"[<:member_join:980085600227065906> Add Me!]"
                                  f"(https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}"
                                  "&permissions=1394047577334&scope=bot%20applications.commands)⠀|⠀"
                                  f"[<:rooBless:980086267360468992> Support Server](https://discord.gg/C3Wz6fRZbV)⠀|⠀"
                                  f"<a:rooLove:980087863477669918> Vote on Top.gg⠀|⠀"
                                  f"<:rooSellout:980086802834681906> Donate\n{'-'*60}\n"
                                  f"**Ping**: `{round(self.bot.latency * 1000)}ms` | "
                                  f"**Uptime**: `{time_to_string(time() - self.bot.uptime)}` | "
                                  f"**Version**: `{SETTINGS['Version']}`\n{'-'*60}")

        if extension is None:
            for cog in self.bot.cogs:
                cog = self.bot.get_cog(cog)

                try:
                    if not cog.public:
                        continue
                except AttributeError:
                    pass
                embed.add_field(name=cog.qualified_name, value=f"**/**`help {cog.qualified_name.lower()}`")
        else:
            if self.bot.get_cog(extension) is None:
                matches = get_close_matches(extension, self.bot.cogs, n=1)
                if len(matches) == 0:
                    await ctx.respond(f"❌ `{extension}` is **not valid**.")
                    return
                extension = str(matches[0])
            extension = self.bot.get_cog(extension)

            embed.title = f"{extension.qualified_name} Help"
            embed.description += f"\n{extension.description}"
            client_permissions = get_permissions(ctx.author.guild_permissions)

            for command in extension.walk_commands():  # Iterate through all commands in cog
                if isinstance(command.parent, SlashCommandGroup) and ctx.guild is not None:
                    # TODO: WORK WITH SYNCED COMMANDS
                    required_permissions = get_permissions(command.parent.default_member_permissions)
                    if not all(elem in client_permissions for elem in required_permissions):  # False -> perm granted
                        continue
                elif ctx.guild is not None:
                    required_permissions = get_permissions(command.default_member_permissions)
                    if not all(elem in client_permissions for elem in required_permissions):  # False -> perm granted
                        continue
                embed.add_field(name=f"/{command.qualified_name}", value=f"`{command.description}`", inline=False)
        await ctx.respond(embed=embed)


def setup(bot: Bot):
    bot.add_cog(Utilities(bot))
