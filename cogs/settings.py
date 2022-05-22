from discord import Bot, SlashCommandGroup, CommandPermission, ApplicationContext, Option, CategoryChannel
from discord.ext.commands import Cog

from data.db.memory import database


def values_valid(option: str, value: str) -> bool:
    if " - " in option:  # True if options are an area of integers
        values = option.split(": ")[1].replace("[", "").replace("]", "").split(" - ")
        try:
            value = float(value)
            if value > int(values[1]) or value < int(values[0]):
                raise ValueError
        except ValueError:
            return False
        return True

    values = option.split(": ")[1].replace("[", "").replace("]", "").lower().split(" | ")
    if value in values:
        return True
    return False


class Settings(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx: ApplicationContext):
        database.cursor().execute("""INSERT OR IGNORE INTO settings (GuildID) VALUES (?)""", (ctx.guild.id,))

    settings = SlashCommandGroup("settings", "Change the bots settings on this server.",
                                 permissions=[CommandPermission("manage_guild", 2, True)])

    ticket_settings = settings.create_subgroup("tickets_setup", "Ticket settings.")

    @settings.command()
    async def music(self, ctx: ApplicationContext,
                    option: Option(str, "Select an option.", choices=["embed size: [Small | Medium | Large]",
                                                                      "delete embed when finished: [True | False]"],
                                   required=True), value: Option(str, "Set a value.", required=True)):
        """Configure the music player."""
        await ctx.defer(ephemeral=True)

        if not values_valid(option, value.lower()):
            await ctx.respond(f"❌ **{value} is not valid** for {option.split(': ')[0]}.\n"
                              "👉 **Valid options are** shown **in the brackets** behind the option.", ephemeral=True)
            return

        options = {"embed size": """UPDATE settings SET MusicEmbedSize = (?) WHERE GuildID = ?""",
                   "delete embed when finished": """UPDATE settings SET MusicDeleteEmbedAfterSong = (?) 
                                                    WHERE GuildID = ?"""}
        values = {"embed size": {"large": 2, "medium": 1, "small": 0},
                  "delete embed when finished": {"true": 1, "false": 0}}
        value = value.lower()
        option = option.split(": ")[0]

        cur = database.cursor()
        cur.execute(options[option], (values[option][value], ctx.guild_id))
        self.bot.get_cog("Music").get_voice_state(ctx).__setattr__(options[option].replace(" ", "_"),
                                                                   (values[option][value]))
        await ctx.respond(f"✅ **{option}** has been **set to {value}**.", ephemeral=True)

    @settings.command()
    async def experience(self, ctx: ApplicationContext,
                         option: Option(str, "Select an option.", choices=["enabled: [True | False]",
                                                                           "multiplier: [1 - 5]"],
                                        required=True), value: Option(str, "Set a value.", required=True)):
        """Configure the leveling."""
        await ctx.defer(ephemeral=True)

        if not values_valid(option, value.lower()):
            await ctx.respond(f"❌ **{value} is not valid** for {option.split(': ')[0]}.\n"
                              "👉 **Valid options are** shown **in the brackets** behind the option.", ephemeral=True)
            return

        options = {"enabled": """UPDATE settings SET ExpIsActivated = (?) WHERE GuildID = ?""",
                   "multiplier": """UPDATE settings SET ExpMultiplication = (?) WHERE GuildID = ?"""}
        values = {"enabled": {"true": 1, "false": 0}}

        try:
            values["multiplier"] = {value: float(value)}
        except ValueError:
            pass
        option = option.split(": ")[0]

        cur = database.cursor()
        cur.execute(options[option], (values[option][value], ctx.guild_id))
        await ctx.respond(f"✅ **{option}** has been **set to {value}**.", ephemeral=True)

    @settings.command()
    async def tickets(self, ctx: ApplicationContext,
                      option: Option(str, "Select an option.", choices=["voice channel: [True | False]"],
                                     required=True), value: Option(str, "Set a value.", required=True)):
        """Configure the ticket system."""
        await ctx.defer(ephemeral=True)

        if not values_valid(option, value.lower()):
            await ctx.respond(f"❌ **{value} is not valid** for {option.split(': ')[0]}.\n"
                              "👉 **Valid options are** shown **in the brackets** behind the option.", ephemeral=True)
            return

        options = {"voice channel": """UPDATE settings SET TicketsCreateVoiceChannel = ? WHERE GuildID = ?"""}
        values = {"voice channel": {"true": 1, "false": 0}}
        option = option.split(": ")[0]

        cur = database.cursor()
        cur.execute(options[option], (values[option][value], ctx.guild_id))
        await ctx.respond(f"✅ **{option}** has been **set to {value}**.", ephemeral=True)

    @ticket_settings.command()
    async def category(self, ctx: ApplicationContext, category: CategoryChannel):
        """Select a category where new tickets should be created."""
        await ctx.defer(ephemeral=True)

        cur = database.cursor()
        if cur.execute("""SELECT TicketsCreateVoiceChannel FROM settings WHERE GuildID = ?""",
                       (ctx.guild.id,)).fetchone() is None:
            cur.execute("""INSERT INTO settings (GuildID, TicketsCreateVoiceChannel) VALUES (?, ?)""",
                        (ctx.guild.id, category.id))
        else:
            cur.execute("""UPDATE settings SET TicketsCreateVoiceChannel = ? WHERE GuildID = ?""",
                        (category.id, ctx.guild.id))
        await ctx.respond(f"✅ New **tickets are now created in** `{category}`.")


def setup(bot: Bot):
    bot.add_cog(Settings(bot))
