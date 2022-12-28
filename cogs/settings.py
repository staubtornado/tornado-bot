from typing import Union, Any

from discord import SlashCommandGroup, Permissions, ApplicationContext, Option
from discord.abc import GuildChannel
from discord.ext.commands import Cog

from bot import CustomBot
from cogs.music import Music
from lib.db.data_objects import GuildSettings, EmbedSize


class Settings(Cog):
    settings: SlashCommandGroup = SlashCommandGroup(
        name="settings",
        description="Change the bots settings on this server.",
        default_member_permissions=Permissions(manage_guild=True)
    )
    music: SlashCommandGroup = settings.create_subgroup(
        name="music",
        description="Change the music settings on this server."
    )
    moderation: SlashCommandGroup = settings.create_subgroup(
        name="moderation",
        description="Change the moderation settings on this server."
    )
    other: SlashCommandGroup = settings.create_subgroup(
        name="other",
        description="Change the other settings on this server."
    )

    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot

    @settings.command(name="experience")
    async def experience_settings(self, ctx: ApplicationContext, enabled: bool, multiplier: int) -> None:
        """Change the experience settings on this server."""

        multiplier = int(multiplier)
        if not 1 <= multiplier <= 5:
            await ctx.respond("❌ **The multiplier must be between 1 and 5**", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild)
        settings.xp_is_activated = enabled
        settings.xp_multiplier = multiplier
        await self.bot.database.update_guild_settings(settings)
        await ctx.respond("✅ **Successfully updated the experience settings**", ephemeral=True)

    @music.command(name="embed")
    async def music_embed(
            self, ctx: ApplicationContext,
            size: Option(
                input_type=str,
                description="Select the size of the song embed.",
                choices=["small", "no queue", "default"],
                required=True),
            refresh: Option(
                input_type=bool,
                description="Refresh the embed after each song.",
                required=True)
    ) -> None:
        """Change the music embed settings on this server."""
        await ctx.defer(ephemeral=True)

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild)
        settings.music_embed_size = EmbedSize({"small": 0, "no queue": 1, "default": 1}[size])
        settings.refresh_music_embed = refresh
        await self.bot.database.update_guild_settings(settings)

        music: Union[Music, Any] = self.bot.get_cog("Music")
        voice_state = music.voice_states.get(ctx.guild.id)

        if voice_state and voice_state.is_valid:
            voice_state.embed_size = EmbedSize({"small": 0, "no queue": 1, "default": 1}[size])
            voice_state.update_embed = refresh
        await ctx.respond(f"✅ **Music embed settings updated** on this server.", ephemeral=True)

    @moderation.command(name="audit-log")
    async def moderation_audit_log(self, ctx: ApplicationContext, enabled: bool, channel: GuildChannel) -> None:
        """Change the audit log settings on this server."""
        await ctx.defer(ephemeral=True)

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild)
        settings.generate_audit_log = enabled
        settings.audit_log_channel_id = channel.id
        await self.bot.database.update_guild_settings(settings)
        await ctx.respond(f"✅ **Audit log settings updated** on this server.", ephemeral=True)

    @other.command(name="welcome-message")
    async def other_welcome_message(self, ctx: ApplicationContext, enabled: bool) -> None:
        """Enable or disable the custom welcome message on this server."""
        await ctx.defer(ephemeral=True)

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild)
        settings.welcome_message = enabled
        await self.bot.database.update_guild_settings(settings)
        await ctx.respond(f"✅ **Welcome message settings updated** on this server.", ephemeral=True)


def setup(bot: CustomBot) -> None:
    bot.add_cog(Settings(bot))
