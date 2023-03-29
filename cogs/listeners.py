from typing import Optional

from discord import Guild, Member, Embed, TextChannel, Forbidden, VoiceState, Asset
from discord.ext.commands import Cog
from discord.utils import utcnow

from bot import CustomBot
from data.config.settings import SETTINGS
from lib.db.data_objects import GuildSettings
from lib.logging.gen_welcome_message import generate_welcome_message


class Listeners(Cog):
    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot
        self.public = False

    async def send_audit_log(self, embed: Embed, member: Member) -> None:
        settings: GuildSettings = await self.bot.database.get_guild_settings(member.guild)

        if settings.generate_audit_log and settings.audit_log_channel_id:
            if channel := member.guild.get_channel(settings.audit_log_channel_id):
                try:
                    await channel.send(embed=embed)
                except (Forbidden, AttributeError):
                    pass
                else:
                    return
            settings.generate_audit_log = False
            settings.audit_log_channel_id = None
            await self.bot.database.update_guild_settings(settings)

    @Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        await self.bot.database.create_guild(guild)

        try:
            await guild.owner.send(embed=Embed(
                title="Welcome!",
                description=f"Thanks for adding {self.bot.user.name} to `{guild.name}`.",
                colour=SETTINGS["Colours"]["Default"])
            )
        except Forbidden:
            pass

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild) -> None:
        await self.bot.database.remove_guild(guild)

    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        settings: GuildSettings = await self.bot.database.get_guild_settings(member.guild)
        if not settings.welcome_message:
            return
        channel: TextChannel = member.guild.system_channel
        banner: Optional[Asset] = None
        if settings.has_premium:
            banner = (await self.bot.fetch_user(member.id)).banner
        try:
            await channel.send(
                content=f"👋 **Hello** {member.mention}! **Welcome** to **{member.guild.name}**.",
                file=await generate_welcome_message(member, banner, self.bot.loop)
            )
        except Forbidden:
            settings.welcome_message = False
            await self.bot.database.update_guild_settings(settings)

    @Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        await self.bot.database.remove_member(member)
        settings: GuildSettings = await self.bot.database.get_guild_settings(member.guild)
        if not settings.generate_audit_log:
            return

        embed: Embed = Embed(
            description=f"⬅️ {member.mention} **left this server.**",
            color=SETTINGS["Colours"]["Error"]
        )
        try:
            embed.set_author(name=member, icon_url=member.avatar.url)
        except AttributeError:
            embed.set_author(name=member, icon_url=member.default_avatar)
        await self.send_audit_log(embed, member)

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        if before.channel == after.channel:
            return

        settings: GuildSettings = await self.bot.database.get_guild_settings(member.guild)
        if not settings.generate_audit_log or not settings.audit_log_channel_id:
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
        await self.send_audit_log(embed, member)


def setup(bot):
    bot.add_cog(Listeners(bot))
