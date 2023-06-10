from math import floor
from typing import Optional, Any, Callable, Union
from urllib.parse import urlparse, ParseResultBytes

from discord import Member, VoiceState, VoiceClient, slash_command, Option, VoiceChannel
from discord.ext.commands import Cog

from bot import TornadoBot
from lib.application_context import CustomApplicationContext
from lib.exceptions import YouTubeNotEnabled
from lib.logging import save_traceback
from lib.music.audio_player import AudioPlayer
from lib.music.embeds import Embeds
from lib.music.extraction import YTDLSource
from lib.music.song import Song
from lib.spotify.exceptions import SpotifyNotFound, SpotifyRateLimit, SpotifyException
from lib.spotify.track import Track
from lib.spotify.track_collection import TrackCollection


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

        #  Analyze the search query
        parse_result: ParseResultBytes = urlparse(search)
        if parse_result.netloc == "open.spotify.com":  # If the search query is not a Spotify URL
            functions: dict[str, Callable] = {
                "track": ctx.bot.spotify.get_track,
                "album": ctx.bot.spotify.get_album,
                "playlist": ctx.bot.spotify.get_playlist,
                "artist": ctx.bot.spotify.get_artist
            }
            try:
                result: Any = await functions[str(parse_result.path).split("/")[1]](search)
            except (KeyError, IndexError, SpotifyNotFound):
                await ctx.respond("❌ Invalid Spotify URL.")
                return
            except SpotifyException as e:
                await ctx.respond("❌ **Spotify** API error.")
                if isinstance(e, SpotifyRateLimit):
                    return
                return await save_traceback(e)
        elif parse_result.scheme in ("http", "https"):  # If the search query is another URL
            try:
                result: YTDLSource = await YTDLSource.from_url(ctx, search, loop=self.bot.loop)
            except YouTubeNotEnabled:
                await ctx.respond(embed=Embeds.YOUTUBE_NOT_ENABLED)
                return
        else:  # If the search query is a search query
            result: YTDLSource = await YTDLSource.from_search(
                ctx.author,
                search,
                loop=self.bot.loop
            )

        # Check for valid existing player
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player:
            audio_player = AudioPlayer(ctx)
            self._audio_player[ctx.guild.id] = audio_player

        # Join a voice channel if not already in one
        if not audio_player.voice:
            if not ctx.author.voice:
                await ctx.respond("❌ You are **not connected to a voice channel**.")
                return
            await self.join(ctx)

        if isinstance(result, TrackCollection):
            for track in result:
                audio_player.put(Song(track, ctx.author))
            await ctx.respond(f"🎶 **Added** `{len(result)}` **tracks to the queue**.")
            return
        if isinstance(result, Union[Track, YTDLSource]):
            audio_player.put(Song(result))
            await ctx.respond(f"🎶 **Added** `{result.title}` **to the queue**.")
            return

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
