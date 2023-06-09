from math import floor
from typing import Optional
from urllib.parse import urlparse

from discord import Member, VoiceState, VoiceClient, slash_command, Option, VoiceChannel, Color, Embed
from discord.ext.commands import Cog

from bot import TornadoBot
from lib.application_context import CustomApplicationContext
from lib.exceptions import YouTubeNotEnabled
from lib.music.audio_player import AudioPlayer
from lib.music.extraction import YTDLSource
from lib.music.song import Song


class Music(Cog):
    _audio_player: dict[int, AudioPlayer]

    def __init__(self, bot: TornadoBot) -> None:
        self.bot = bot
        self._audio_player = {}

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        if member.id != self.bot.user.id:
            return
        if before.channel == after.channel:
            return

        player: Optional[AudioPlayer] = self._audio_player.get(member.guild.id)
        voice_client: VoiceClient = member.guild.voice_client  # type: ignore

        if not player:
            return

        if not after.channel:
            player.voice = None
            return
        player.voice = voice_client

        if before.channel is None and after.channel is not None:
            pass

        if before.channel is not None and after.channel is not None:
            voice_client.pause()
            voice_client.resume()

    @slash_command()
    async def join(
            self,
            ctx: CustomApplicationContext,
            destination: Option(
                VoiceChannel,
                "Destination, defaults to the voice channel you are in.",
                required=False
            ) = None
    ) -> None:
        """Joins a voice channel"""

        if destination := destination or ctx.author.voice.channel:
            await destination.connect()
            await ctx.respond(f"👋 **Hello**! **Joined** {destination.mention}.")
            return
        await ctx.respond("❌ You are **not connected to a voice channel**.")

    @slash_command()
    async def play(
            self,
            ctx: CustomApplicationContext,
            search: Option(
                str,
                "The song to play. This can be a search query or a to a playlist.",
                required=True
            )):
        """Plays a song or playlist."""
        await ctx.defer()

        try:
            if urlparse(search).scheme in ("http", "https"):
                result: YTDLSource = await YTDLSource.from_url(ctx, search, loop=self.bot.loop)
            else:
                result: YTDLSource = await YTDLSource.from_search(
                    ctx,
                    f"https://music.youtube.com/search?q={search}#songs",
                    loop=self.bot.loop
                )
        except YouTubeNotEnabled:
            embed: Embed = Embed(
                title="YouTube is not available",
                description=(
                    "Switch to a self hosted bot instance for more customization options.\n"
                    "Read more [here](https://www.gamerbraves.com/youtube-forces-discords-rythm-bot-to-shut-down/)."
                ),
                color=Color.brand_red()
            )
            await ctx.respond(embed=embed)
            return

        if not result:
            await ctx.respond("No results found")
            return

        # Check for valid existing player
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player:
            audio_player = AudioPlayer(ctx)
            self._audio_player[ctx.guild.id] = audio_player

        # Join voice channel if not already in one
        if not audio_player.voice:
            if not ctx.author.voice:
                await ctx.respond("❌ You are **not connected to a voice channel**.")
                return
            await self.join(ctx)

        audio_player.put(Song(result))
        await ctx.respond(f"🎶 **Added** `{result}` **to the queue**.")

    @slash_command()
    async def pause(self, ctx: CustomApplicationContext) -> None:
        """Pauses the currently playing song."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player:
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        if audio_player.voice.is_paused():
            await ctx.respond("❌ **Already paused**.")
            return
        audio_player.voice.pause()
        await ctx.respond("⏸️ **Paused**.")

    @slash_command()
    async def resume(self, ctx: CustomApplicationContext) -> None:
        """Resumes the currently paused song."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player:
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        if not audio_player.voice.is_playing():
            await ctx.respond("❌ **Already playing**.")
            return
        audio_player.voice.resume()
        await ctx.respond("▶️ **Resumed**.")

    @slash_command()
    async def skip(
            self,
            ctx: CustomApplicationContext,
            force: Option(
                str,
                "Force skip the current song.",
                required=False,
                choices=["True"]
            ) = "False"
    ) -> None:
        """Skips the currently playing song."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player:
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        if force == "True" and ctx.author.guild_permissions.manage_guild:
            audio_player.skip()
            await ctx.respond("⏭️ **Force skipped**.")
            return

        if ctx.author.id in audio_player.current.skip_votes:
            await ctx.respond("❌ You have already voted to skip.")
            return

        current: Song = audio_player.current

        majority: int = floor(len([member for member in audio_player.voice.channel.members if not member.bot]) * 0.66)
        if len(current.skip_votes) >= majority:
            audio_player.skip()
            await ctx.respond("⏭️ **Skipped**.")
            return
        current.skip_votes.add(ctx.author.id)
        await ctx.respond(f"🗳️ **Voted to skip**. **{len(current.skip_votes)}/{majority}** votes.")

    @slash_command()
    async def stop(self, ctx: CustomApplicationContext) -> None:
        """Stops the currently playing song."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)

        if not ctx.author.guild_permissions.manage_guild:
            if len([member for member in audio_player.voice.channel.members if not member.bot]) > 3:
                await ctx.respond("❌ You are currently **not authorized** to stop the player.")
                return

        if not audio_player:
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        audio_player.stop()
        await ctx.respond("⏹️ **Stopped**.")




def setup(bot: TornadoBot) -> None:
    bot.add_cog(Music(bot))
