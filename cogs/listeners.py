from sqlite3 import Cursor

from discord import Guild, Member, Embed, Bot, TextChannel, Forbidden, VoiceState
from discord.ext.commands import Cog
from discord.utils import utcnow

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.logging.welcome_message import generate_welcome_message


class Listeners(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.public = False

    async def send_audit_log(self, embed: Embed, row: tuple, member: Member, cursor) -> None:
        channel = self.bot.get_channel(row[1])
        if channel is None:
            cursor.execute(
                """UPDATE guilds SET (GenerateAuditLog = 0, AuditLogChannel = NULL) WHERE GuildID = ?""",
                (member.guild.id,)
            )
            return database.commit()
        try:
            await channel.send(embed=embed)
        except Forbidden:
            cursor.execute(
                """UPDATE guilds SET (GenerateAuditLog = 0, AuditLogChannel = NULL) WHERE GuildID = ?""",
                (member.guild.id,)
            )
            database.commit()

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        cur: Cursor = database.cursor()
        cur.execute("""INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)""", (guild.id,))
        cur.execute("""INSERT OR IGNORE INTO settings (GuildID) VALUES (?)""", (guild.id,))
        database.commit()
        await guild.owner.send(embed=Embed(
            title="Welcome!",
            description=f"Thanks for adding TornadoBot to `{guild.name}`.",
            colour=SETTINGS["Colours"]["Default"])
        )

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        cur: Cursor = database.cursor()
        cur.execute("""DELETE FROM experience WHERE GuildID = ?""", (guild.id,))
        cur.execute("""DELETE FROM settings WHERE GuildID = ?""", (guild.id,))
        cur.execute("""DELETE FROM subjects WHERE GuildID = ?""", (guild.id,))
        database.commit()

    @Cog.listener()
    async def on_member_join(self, member: Member):
        cur: Cursor = database.cursor()
        cur.execute(
            """INSERT OR IGNORE INTO settings (GuildID) VALUES (?)""",
            (member.guild.id,)
        )
        cur.execute(
            """SELECT WelcomeMessage FROM settings WHERE GuildID = ?""",
            (member.guild.id,)
        )

        if not cur.fetchone()[0]:
            return

        channel: TextChannel = member.guild.system_channel

        try:
            await channel.send(
                content=f"👋 **Hello** {member.mention}! **Welcome** to **{member.guild.name}**.",
                file=await generate_welcome_message(member)
            )
        except Forbidden:
            cur.execute(
                """UPDATE settings SET (WelcomeMessage) = (?) WHERE GuildID = ?""",
                (0, member.guild.id)
            )

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        cur: Cursor = database.cursor()

        cur.execute(
            """DELETE from experience WHERE GuildID = ? AND UserID = ?""",
            (member.guild.id, member.id)
        )

        cur.execute(
            """SELECT GenerateAuditLog, AuditLogChannel FROM settings WHERE GuildID = ?""",
            (member.guild.id,)
        )
        data: tuple[int, ...] = cur.fetchone()

        if not data[0]:
            return database.commit()

        embed: Embed = Embed(
            description=f"⬅️ {member.mention} **left this server.**",
            color=SETTINGS["Colours"]["Error"]
        )
        try:
            embed.set_author(name=member, icon_url=member.avatar.url)
        except AttributeError:
            embed.set_author(name=member, icon_url=member.default_avatar)
        await self.send_audit_log(embed, data, member, cur)

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if before.channel == after.channel:
            return

        cur: Cursor = database.cursor()
        cur.execute(
            """SELECT GenerateAuditLog, AuditLogChannel FROM settings WHERE GuildID = ?""",
            (member.guild.id,)
        )
        data = cur.fetchone()

        if not data[0]:
            return

        embed: Embed = Embed(timestamp=utcnow())

        if before.channel is None:
            embed.description = f"⬆️️ {member.mention} **joined** {after.channel.mention}**.**"
            embed.colour = 0x57F287

        elif after.channel is None:
            embed.description = f"⬇️️ {member.mention} **left** {before.channel.mention}**.**"
            embed.colour = 0xED4245
        else:
            embed.description = (f"↕️️️ {member.mention} **switched from** {before.channel.mention} **to**"
                                 f" {after.channel.mention}**.**")
            embed.colour = 0x5865F2

        try:
            embed.set_author(name=member, icon_url=member.avatar.url)
        except AttributeError:
            embed.set_author(name=member, icon_url=member.default_avatar)
        await self.send_audit_log(embed, data, member, cur)


def setup(bot):
    bot.add_cog(Listeners(bot))
