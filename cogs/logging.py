from datetime import datetime

from discord import Guild, Member, Embed, Forbidden, HTTPException, VoiceState, slash_command
from discord.ext.commands import Cog

from bot import TornadoBot
from lib.contexts import CustomApplicationContext
from lib.db.db_classes import GuildSettings, Emoji
from lib.logging import log
from lib.stats_view import generate_stats_card
from lib.welcome_message import generate_welcome_message_card


class Logging(Cog):
    def __init__(self, bot: TornadoBot) -> None:
        self.bot = bot

    async def _final_log_channel_logic(self, embed: Embed, guild_settings: GuildSettings) -> None:
        """
        Send the embed to the log channel if it exists, otherwise remove the log channel from the database.

        :param embed: The embed to send.
        :param guild_settings: The guild settings.
        :return: None
        """

        if channel := self.bot.get_channel(guild_settings.log_channel_id):
            try:
                await channel.send(embed=embed)
            except (Forbidden, HTTPException):
                pass
            return
        guild_settings.log_channel_id = None
        await self.bot.database.set_guild_settings(guild_settings)

    @Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        log(f"Joined guild {repr(guild)}")

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild) -> None:
        log(f"Left guild {repr(guild)}")
        await self.bot.database.remove_guild_settings(guild.id)
        await self.bot.database.remove_leveling_stats(None, guild.id)

    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        guild_settings: GuildSettings = await self.bot.database.get_guild_settings(member.guild.id)

        if guild_settings.send_welcome_message:
            if channel := member.guild.system_channel:
                try:
                    await channel.send(
                        content=guild_settings.welcome_message.format(user=member.mention, guild=member.guild),
                        file=await generate_welcome_message_card(member)
                    )
                except (Forbidden, HTTPException):
                    pass
            else:
                guild_settings.send_welcome_message = False
                await self.bot.database.set_guild_settings(guild_settings)

        emoji_checkmark: Emoji = await self.bot.database.get_emoji("checkmark")

        embed: Embed = Embed(
            description=f"{emoji_checkmark} {member.mention} **joined** the **server**.",
            timestamp=member.joined_at,
            color=0xCDEAC0
        )
        embed.set_author(name=member.name, icon_url=member.avatar.url)
        await self._final_log_channel_logic(embed, guild_settings)

    @Cog.listener()
    async def on_member_remove(self, member: Member) -> None:
        guild_settings: GuildSettings = await self.bot.database.get_guild_settings(member.guild.id)
        if not guild_settings.log_channel_id:
            return

        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")
        embed: Embed = Embed(
            description=f"{emoji_cross} {member.mention} **left** the **server**.",
            timestamp=datetime.utcnow(),
            color=0xFF928B
        )
        embed.set_author(name=member.name, icon_url=member.avatar.url)
        await self._final_log_channel_logic(embed, await self.bot.database.get_guild_settings(member.guild.id))

    @Cog.listener()
    async def on_voice_state_update(
            self,
            member: Member,
            before: VoiceState,
            after: VoiceState
    ) -> None:
        if before.channel == after.channel:
            return

        guild_settings: GuildSettings = await self.bot.database.get_guild_settings(member.guild.id)
        if not guild_settings.log_channel_id:
            return

        embed: Embed = Embed(
            timestamp=datetime.utcnow(),
        )

        if before.channel is None:
            emoji_skip: Emoji = await self.bot.database.get_emoji("skip")
            embed.description = f"{emoji_skip} {member.mention} **joined** {after.channel.mention}."
            embed.colour = 0xCDEAC0
        elif after.channel is None:
            emoji_back: Emoji = await self.bot.database.get_emoji("back")
            embed.description = f"{emoji_back} {member.mention} **left** {before.channel.mention}."
            embed.colour = 0xC5C3EE
        else:
            emoji_shuffle: Emoji = await self.bot.database.get_emoji("shuffle")
            embed.description = (
                f"{emoji_shuffle} {member.mention} **moved from** {before.channel.mention} **to** "
                f"{after.channel.mention}."
            )
            embed.colour = 0xEEC3E6

        embed.set_author(name=member.name, icon_url=member.avatar.url)
        await self._final_log_channel_logic(embed, await self.bot.database.get_guild_settings(member.guild.id))

    @slash_command()
    async def stats(
            self,
            ctx: CustomApplicationContext,
            user: Member = None
    ) -> None:
        """Shows the stats of a user."""

        await ctx.defer()

        target: Member = user or ctx.author
        stats = await self.bot.database.get_user_stats(target.id)
        await ctx.respond(
            file=await generate_stats_card(target, stats, self.bot.loop),
        )


def setup(bot: TornadoBot) -> None:
    bot.add_cog(Logging(bot))
