from difflib import get_close_matches
from time import time

from discord import Bot, slash_command, ApplicationContext, AutocompleteContext, Option, Embed, SlashCommandGroup
from discord.ext.commands import Cog

from data.config.settings import SETTINGS
from lib.utils.utils import time_to_string, get_permissions, create_graph




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


class Utilities(Cog):
    """
    Useful commands for moderators, server owners and information about the bot.
    """
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command()
    async def ping(self, ctx: ApplicationContext):
        """Check the bots ping to the Discord API."""
        self.bot.latencies.append(round(self.bot.latency * 1000))

        embed = Embed(title="Ping", description="The bots ping to the Discord API.",
                      colour=SETTINGS["Colours"]["Default"])
        embed.add_field(name="Ping", value=f"`{round(self.bot.latency * 1000)}`**ms**")

        image, file = create_graph(self.bot.latencies)
        embed.set_image(url=image)
        await ctx.respond(embed=embed, file=file)

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

            try:
                client_permissions = get_permissions(ctx.author.guild_permissions)
            except AttributeError:
                client_permissions = []

            for command in extension.walk_commands():  # Iterate through all commands in cog
                if isinstance(command.parent, SlashCommandGroup) and client_permissions:
                    # TODO: WORK WITH SYNCED COMMANDS
                    required_permissions = get_permissions(command.parent.default_member_permissions)
                    if not all(elem in client_permissions for elem in required_permissions):  # False -> perm granted
                        continue
                elif client_permissions:
                    required_permissions = get_permissions(command.default_member_permissions)
                    if not all(elem in client_permissions for elem in required_permissions):  # False -> perm granted
                        continue
                embed.add_field(name=f"/{command.qualified_name}", value=f"`{command.description}`", inline=False)
        await ctx.respond(embed=embed)


def setup(bot: Bot):
    bot.add_cog(Utilities(bot))
