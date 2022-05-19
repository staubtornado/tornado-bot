from discord import Bot, SlashCommandGroup, CommandPermission, ApplicationContext, Option
from discord.ext.commands import Cog

from data.db.memory import database


class Settings(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    settings = SlashCommandGroup("settings", "Change the bots settings on this server.",
                                 permissions=[CommandPermission("manage_guild", 2, True)])

    music_settings = settings.create_subgroup("music", "Music settings.")
    experience_settings = settings.create_subgroup("experience", "Experience settings.")

    @music_settings.command()
    async def embed(self, ctx: ApplicationContext,
                    size: Option(str, "Change the song embed size.", choices=["Large", "Medium", "Small"],
                                 required=True)):
        """Change the embed style of songs."""
        values = {"Large": 2, "Medium": 1, "Small": 0}

        cur = database.cursor()
        if cur.execute("""SELECT MusicEmbedSize from settings WHERE GuildID = ?""", (ctx.guild.id, )).fetchone() is \
                None:
            cur.execute("""INSERT INTO settings (GuildID, MusicEmbedSize) VALUES (?, ?)""", (ctx.guild.id,
                                                                                             values[size]))
        else:
            cur.execute("""Update settings SET MusicEmbedSize = ? WHERE GuildID = ?""",
                        (values[size], ctx.guild.id))

        await ctx.respond(f"**Changed size** of song embeds **to {size}**.")

    @experience_settings.command()
    async def enabled(self, ctx: ApplicationContext, state: bool):
        pass


def setup(bot: Bot):
    bot.add_cog(Settings(bot))
