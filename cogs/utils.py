from datetime import datetime
from difflib import get_close_matches
from json import loads
from re import sub
from time import time, strptime, mktime

from discord import Bot, slash_command, ApplicationContext, AutocompleteContext, Option, Embed, SlashCommandGroup
from discord.ext.commands import Cog
from requests import get

from data.config.settings import SETTINGS
from lib.utils.utils import time_to_string, get_permissions, create_graph


def get_releases() -> list[str]:
    rtrn: list = []
    rtrn.extend([tag["name"] for tag in loads(get("https://api.github.com/repos/staubtornado/tornado-bot/tags").text)])
    return rtrn


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
    Useful commands and information about the bot.
    """
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command()
    async def ping(self, ctx: ApplicationContext):
        """Check the bot's ping to the Discord API."""
        await ctx.defer()

        self.bot.latencies.append(round(self.bot.latency * 1000))

        embed = Embed(title="Ping", description="The bot's ping to the Discord API.",
                      colour=SETTINGS["Colours"]["Default"])
        embed.add_field(name="Ping", value=f"`{round(self.bot.latency * 1000)}`**ms**")

        image, file = create_graph(self.bot.latencies)
        embed.set_image(url=image)
        await ctx.respond(embed=embed, file=file)

    @slash_command()
    async def uptime(self, ctx: ApplicationContext):
        """Check the bots' uptime."""
        await ctx.respond(f"⏱ **Uptime**: {time_to_string(time() - self.bot.uptime)}")

    @slash_command()
    async def help(self, ctx: ApplicationContext,
                   extension: Option(str, description="Select an extension for which you want to receive precise "
                                                      "information.", autocomplete=get_cogs, required=False) = None):
        """Get a list of features and information about the bot."""
        embed = Embed(title="Help", colour=SETTINGS["Colours"]["Default"],
                      description=f"[<:member_join:980085600227065906> Add Me!]"
                                  f"(https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}"
                                  "&permissions=1394047577334&scope=bot%20applications.commands)⠀**|**⠀"
                                  f"[<:rooBless:980086267360468992> Support Server](https://discord.gg/C3Wz6fRZbV)⠀"
                                  f"**|**⠀<a:rooLove:980087863477669918> Vote on Top.gg⠀**|**⠀"
                                  f"<:rooSellout:980086802834681906> Donate\n{'-'*82}\n"
                                  f"**Ping**: `{round(self.bot.latency * 1000)}ms` | "
                                  f"**Uptime**: `{time_to_string(time() - self.bot.uptime)}` | "
                                  f"**Version**: [`{SETTINGS['Version']}`](https://github.com/staubtornado/tornado-bot)"
                                  f"\n{'-'*82}")

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

    @slash_command()
    async def news(self, ctx: ApplicationContext,
                   version: Option(str, description="Select a version.", required=False, choices=get_releases())):
        """Latest changelog and version info about the bot."""
        await ctx.defer()

        try:
            version: str = version or get_releases()[0]
            embed: Embed = Embed(title=f"{version} Changes", description="", colour=SETTINGS["Colours"]["Default"])

            for tag in loads(get("https://api.github.com/repos/staubtornado/tornado-bot/tags").text):
                if isinstance(version, dict):
                    version: tuple[dict[str, dict], dict[str, dict]] = tag, version
                    break

                if tag["name"] == version:
                    version = tag

            old: str = version[0]['commit']['sha']
            new: str = version[1]['commit']['sha']
        except (KeyError, IndexError, TypeError):
            await ctx.respond(f"❌ **Cannot get any news**. Please **try again later**.")
            return

        response: dict = loads(get(f"https://api.github.com/repos/staubtornado/tornado-bot/compare/{old}...{new}").text)
        for commit in response["commits"]:
            row: str = f"[`{commit['sha'][0:6]}`]({commit['html_url']}) {commit['commit']['message']}\n"

            if not len(row) + len(embed.description) > 3896:
                embed.description += row
                continue
            embed.description += f"\n**[View More]({response['html_url']})**"
            break

        latest_commit: dict = response['commits'][-1]
        date: str = latest_commit['commit']['committer']['date'].replace("T", " ").replace("Z", "")
        date_time_obj: datetime = datetime.fromtimestamp(mktime(strptime(date, "%Y-%m-%d %H:%M:%S")))

        embed.description = f"Published <t:{str(date_time_obj.timestamp())[:-2]}:R>\n\n" + embed.description
        embed.set_footer(text=f"{response['total_commits']} commits")

        await ctx.respond(embed=embed)

    @slash_command()
    async def feedback(self, ctx: ApplicationContext, message: str):
        """Send feedback to the bot's owners."""
        embed: Embed = Embed(title="New Feedback", colour=SETTINGS["Colours"]["Default"])
        embed.add_field(name="By", value=str(ctx.author.id), inline=True)
        embed.add_field(name="On", value=str(ctx.guild_id), inline=True)
        embed.add_field(name="Feedback", value=message, inline=False)

        await self.bot.get_user(self.bot.owner_ids[0]).send(embed=embed)
        await ctx.respond("🛫 **Thanks**! Your **feedback** has been **registered**.", ephemeral=True)

    @slash_command()
    async def whois(self, ctx: ApplicationContext, ip: str):
        await ctx.defer()

        response = get(f'https://ipapi.co/{ip}/json/').json()
        content: list[str, None] = [response.get("city"), response.get("region"), response.get("country_name")]

        if all(content):
            await ctx.respond("**🗺️ {}**".format(sub(r"[\[\]']", "", str(content).replace(', ', '** in **'))))
            return
        await ctx.respond("❌ Given input is **not a valid IP**.")


def setup(bot: Bot):
    bot.add_cog(Utilities(bot))
