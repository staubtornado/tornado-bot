from discord import Bot, SlashCommandGroup, CommandPermission, ApplicationContext, Option, CategoryChannel
from discord.ext.commands import Cog

from data.db.memory import database


class Settings(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    settings = SlashCommandGroup("settings", "Change the bots settings on this server.",
                                 permissions=[CommandPermission("manage_guild", 2, True)])

    music_settings = settings.create_subgroup("music", "Music settings.")
    experience_settings = settings.create_subgroup("experience", "Experience settings.")
    ticket_settings = settings.create_subgroup("tickets", "Ticket settings.")

    @music_settings.command()
    async def embed(self, ctx: ApplicationContext,
                    size: Option(str, "Change the song embed size.", choices=["Large", "Medium", "Small"],
                                 required=True)):
        """Change the embed style of songs."""
        await ctx.defer(ephemeral=True)
        values = {"Large": 2, "Medium": 1, "Small": 0}

        cur = database.cursor()
        if cur.execute("""SELECT MusicEmbedSize FROM settings WHERE GuildID = ?""",
                       (ctx.guild.id, )).fetchone() is None:
            cur.execute("""INSERT INTO settings (GuildID, MusicEmbedSize) VALUES (?, ?)""",
                        (ctx.guild.id, values[size]))
        else:
            cur.execute("""UPDATE settings SET MusicEmbedSize = ? WHERE GuildID = ?""", (values[size], ctx.guild.id))
        self.bot.get_cog("Music").get_voice_state(ctx).embed_size = values[size]

        await ctx.respond(f"✅ **Changed size** of song embeds **to {str(size).lower()}**.", ephemeral=True)

    @experience_settings.command()
    async def enabled(self, ctx: ApplicationContext, state: bool):
        """Enable / disable the experience system."""
        await ctx.defer(ephemeral=True)

        cur = database.cursor()
        if cur.execute("""SELECT ExpIsActivated FROM settings WHERE GuildID = ?""",
                       (ctx.guild.id, )).fetchone() is None:
            cur.execute("""INSERT INTO settings (GuildID, ExpIsActivated) VALUES (?, ?)""", (ctx.guild.id, int(state)))
        else:
            cur.execute("""UPDATE settings SET ExpIsActivated = ? WHERE GuildID = ?""", (int(state), ctx.guild.id))

        response = "Disabled"
        if state:
            response = "Enabled"
        await ctx.respond(f"✅ **{response}** the **experience system** on this server.", ephemeral=True)

    @experience_settings.command()
    async def multiplier(self, ctx: ApplicationContext, multiplier: str):
        """Change the multiplier of gained XP per message."""
        await ctx.defer(ephemeral=True)

        try:
            multiplier = float(multiplier)
            if multiplier > 5 or not multiplier > 1:
                raise ValueError
        except ValueError:
            await ctx.respond("❌ The **multiplier has to be between 0 and 5**.", ephemeral=True)
            return

        cur = database.cursor()
        if cur.execute("""SELECT ExpMultiplication FROM settings WHERE GuildID = ?""",
                       (ctx.guild.id, )).fetchone() is None:
            cur.execute("""INSERT INTO settings (GuildID, ExpMultiplication) VALUES (?, ?)""",
                        (ctx.guild.id, multiplier))
        else:
            cur.execute("""UPDATE settings SET ExpMultiplication = ? WHERE GuildID = ?""",
                        (multiplier, ctx.guild.id))
        await ctx.respond(f"✅ The XP **multiplier** has been **set to** `{multiplier}`.")

    @ticket_settings.command()
    async def voice(self, ctx: ApplicationContext, setting: bool):
        """Select if tickets should also have a voice channel."""
        await ctx.defer(ephemeral=True)

        cur = database.cursor()
        if cur.execute("""SELECT TicketsCreateVoiceChannel FROM settings WHERE GuildID = ?""",
                       (ctx.guild.id, )).fetchone() is None:
            cur.execute("""INSERT INTO settings (GuildID, TicketsCreateVoiceChannel) VALUES (?, ?)""",
                        (ctx.guild.id, int(setting)))
        else:
            cur.execute("""UPDATE settings SET TicketsCreateVoiceChannel = ? WHERE GuildID = ?""",
                        (int(setting), ctx.guild.id))
        response = "no longer"
        if setting:
            response = "now"
        await ctx.respond(f"✅ New **tickets {response} have** a **voice channel**.")

    @ticket_settings.command()
    async def category(self, ctx: ApplicationContext, category: CategoryChannel):
        """Select a category where new tickets should be created."""
        await ctx.defer(ephemeral=True)

        cur = database.cursor()
        if cur.execute("""SELECT TicketsCreateVoiceChannel FROM settings WHERE GuildID = ?""",
                       (ctx.guild.id, )).fetchone() is None:
            cur.execute("""INSERT INTO settings (GuildID, TicketsCreateVoiceChannel) VALUES (?, ?)""",
                        (ctx.guild.id, category.id))
        else:
            cur.execute("""UPDATE settings SET TicketsCreateVoiceChannel = ? WHERE GuildID = ?""",
                        (category.id, ctx.guild.id))
        await ctx.respond(f"✅ New **tickets are now created in** `{category}`.")


def setup(bot: Bot):
    bot.add_cog(Settings(bot))
