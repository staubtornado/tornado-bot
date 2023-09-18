from discord import SlashCommandGroup, Permissions, Option, TextChannel
from discord.ext.commands import Cog

from bot import TornadoBot
from cogs.music import Music
from lib.contexts import CustomApplicationContext
from lib.db.db_classes import GuildSettings
from lib.enums import SongEmbedSize
from lib.music.audio_player import AudioPlayer


class Configuration(Cog):
    def __init__(self, bot: TornadoBot) -> None:
        self.bot = bot

    config: SlashCommandGroup = SlashCommandGroup(
        name="settings",
        description="Configure the bot.",
        default_member_permissions=Permissions(manage_guild=True)
    )
    music: SlashCommandGroup = config.create_subgroup(
        name="music",
        description="Configure the music cog."
    )
    leveling: SlashCommandGroup = config.create_subgroup(
        name="leveling",
        description="Configure the leveling cog."
    )
    moderation: SlashCommandGroup = config.create_subgroup(
        name="moderation",
        description="Configure the moderation cog."
    )

    @music.command(
        name="embed",
        description="Set the embed size for the song embeds.",
    )
    async def music_embed(
            self,
            ctx: CustomApplicationContext,
            size: Option(str, "The size of the embed.", required=True, choices=["small", "withoutQueue", "default"])
    ) -> None:
        """
        Set the embed size for the music embeds.

        :param ctx: The context.
        :param size: The size of the embed.
        :return: None
        """
        await ctx.defer(ephemeral=True)

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild.id)
        settings.song_embed_size = {
            "small": SongEmbedSize.SMALL,
            "withoutQueue": SongEmbedSize.NO_QUEUE,
            "default": SongEmbedSize.DEFAULT
        }[size]
        await self.bot.database.set_guild_settings(settings)

        cog: Cog = self.bot.get_cog("Music")
        if isinstance(cog, Music):
            try:
                audio_player: AudioPlayer = cog[ctx.guild.id]
            except KeyError:
                pass
            else:
                audio_player.embed_size = settings.song_embed_size
        await ctx.respond(f"**Set** the **embed size** to `{size}`.", ephemeral=True)

    @leveling.command(
        name="toggle",
        description="Enable or disable the leveling system.",
    )
    async def leveling_toggle(
            self,
            ctx: CustomApplicationContext,
    ) -> None:
        """
        Toggle the leveling cog.

        :param ctx: The context.
        :return: None
        """
        await ctx.defer(ephemeral=True)

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild.id)
        settings.xp_active = not settings.xp_active
        await self.bot.database.set_guild_settings(settings)
        await ctx.respond(f"**Set** the **leveling system** to `{settings.xp_active}`.", ephemeral=True)

    @leveling.command(
        name="multiplier",
        description="Set the leveling multiplier. The default is 1.",
    )
    async def leveling_multiplier(
            self,
            ctx: CustomApplicationContext,
            multiplier: Option(int, "The multiplier.", required=True)
    ) -> None:
        """
        Set the leveling multiplier.

        :param ctx: The context.
        :param multiplier: The multiplier.
        :return: None
        """

        if not 0 < multiplier <= 5:
            await ctx.respond(f"**Error:** The multiplier must be between `1 and 5`.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild.id)
        settings.xp_multiplier = multiplier
        await self.bot.database.set_guild_settings(settings)
        await ctx.respond(f"**Set** the **leveling multiplier** to `{multiplier}`.", ephemeral=True)

    @moderation.command(
        name="channel",
        description="Channel, where the moderation logs will be sent. If empty, it will be disabled.",
    )
    async def moderation_channel(
            self,
            ctx: CustomApplicationContext,
            channel: Option(TextChannel, "The channel.", required=False) = None
    ) -> None:
        """
        Set the moderation channel.

        :param ctx: The context.
        :param channel: The channel.
        :return: None
        """
        await ctx.defer(ephemeral=True)

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild.id)
        settings.log_channel_id = channel.id if channel else None
        await self.bot.database.set_guild_settings(settings)
        await ctx.respond(
            content=f"**Set** the **moderation channel** to {channel.mention if channel else '`None`'}.",
            ephemeral=True
        )

    @moderation.command(
        name="welcome",
        description="Edit, enable or disable the welcome message.",
    )
    async def moderation_welcome(
            self,
            ctx: CustomApplicationContext,
            enabled: Option(
                input_type=str,
                description="Enable or disable the welcome message.",
                required=False,
                default="True",
                choices=["True", "False"]
            ),
            message: Option(
                input_type=str,
                description="The message. {user}, {guild} are placeholders.",
                required=False,
                default="Welcome {user} to {guild}!"
            )
    ) -> None:
        """
        Set the welcome message.

        :param ctx: The context.
        :param enabled: Enable or disable the welcome message.
        :param message: The message.
        :return: None
        """

        if len(message) > 100:
            await ctx.respond(f"**Error:** The message must be shorter than `100` characters.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)

        settings: GuildSettings = await self.bot.database.get_guild_settings(ctx.guild.id)
        settings.send_welcome_message = {"True": True, "False": False}[enabled]
        settings.welcome_message = message
        await self.bot.database.set_guild_settings(settings)
        message = message.replace("{user}", "@user").replace("{guild}", "@guild")

        if not settings.send_welcome_message:
            await ctx.respond(f"**Disabled** the **welcome message**.", ephemeral=True)
            return
        await ctx.respond(f"**Set** the **welcome message** to `{message}`.", ephemeral=True)


def setup(bot: TornadoBot) -> None:
    bot.add_cog(Configuration(bot))
