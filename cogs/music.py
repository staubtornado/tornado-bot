from math import floor, ceil
from random import shuffle
from re import match
from typing import Optional, Callable, Union
from urllib.parse import urlparse, ParseResultBytes

from discord import Member, VoiceState, VoiceClient, slash_command, Option, VoiceChannel, Embed, Color
from discord.ext.commands import Cog
from yt_dlp import DownloadError

from bot import TornadoBot
from lib.contexts import CustomApplicationContext
from lib.db.emoji import Emoji
from lib.exceptions import YouTubeNotEnabled
from lib.logging import save_traceback
from lib.music.audio_player import AudioPlayer
from lib.music.auto_complete import complete
from lib.music.embeds import Embeds
from lib.music.extraction import YTDLSource
from lib.music.song import Song
from lib.spotify.artist import Artist
from lib.spotify.exceptions import SpotifyNotFound, SpotifyRateLimit, SpotifyException
from lib.spotify.track import Track
from lib.spotify.track_collection import TrackCollection
from lib.utils import format_time


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
    async def leave(self, ctx: CustomApplicationContext) -> None:
        """Leaves a voice channel, requires 50% approval. DJ permissions override this."""

        # If the bot is not connected to a voice channel
        if not ctx.guild.voice_client:
            await ctx.respond("❌ I am **not connected to a voice channel**.")
            return

        # Check if the user is a DJ
        is_dj: bool = ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]
        if is_dj:
            await ctx.guild.voice_client.disconnect(force=False)
            await ctx.respond("👋 **Goodbye**!")
            return

        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)

        # Add a vote to leave and check if the vote was successful
        vote: tuple[int, int, bool] = audio_player.vote(audio_player.leave, ctx.author.id, 0.5)
        if vote[2]:
            await ctx.guild.voice_client.disconnect(force=False)
            await ctx.respond("👋 **Goodbye**!")
            return
        percent: int = floor((vote[0] / vote[1]) * 100)
        await ctx.respond(f"🗳️ **Vote to stop** the player. {vote[0]}/{vote[1]} (**{percent}%**)")

    @slash_command()
    async def play(
            self,
            ctx: CustomApplicationContext,
            search: Option(
                str,
                "The song to play. This can be a search query or a to a playlist.",
                required=True,
                autocomplete=complete
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
                m = match(r"(https://)?open.spotify\.com/(intl-\w+/)?(track|album|artist|playlist)/(\w+)", search)
                if not m:
                    raise SpotifyNotFound
                result = await functions[m.group(3)](search)
            except (KeyError, SpotifyNotFound):
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
            except DownloadError:
                await ctx.respond("❌ **Download error**. Try a different source.")
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
        if isinstance(result, Artist):
            for track in result.top_tracks:
                audio_player.put(Song(track, ctx.author))
            await ctx.respond(f"🎶 **Added** `{len(result.top_tracks)}` **tracks to the queue**.")
            return
        if isinstance(result, Union[Track, YTDLSource]):
            audio_player.put(Song(result, ctx.author))
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
        """Skips current song, requires 33% approval. The requester can always skip."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player:
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        # Check if the user is the requester
        if ctx.author.id == audio_player.current.requester.id:
            audio_player.skip()
            await ctx.respond("⏭️ **Skipped**.")
            return

        # Check if the user is a DJ and force skip
        is_dj: bool = ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]
        if force == "True":
            if not is_dj:
                await ctx.respond("❌ You are **not a DJ**.")
                return
            audio_player.skip()
            await ctx.respond("⏭️ **Force skipped**.")
            return

        # Add a vote and check if the song should be skipped
        vote: tuple[int, int, bool] = audio_player.vote(audio_player.skip, ctx.author.id, 0.33)
        if vote[2]:
            await ctx.respond("🗳️ **Voted to skip** the song.")
            return
        percent: int = round(vote[0] / vote[1] * 100)
        await ctx.respond(f"🗳️ **Vote to skip** the song. {vote[0]}/{vote[1]} (**{percent}%**)")

    @slash_command()
    async def stop(self, ctx: CustomApplicationContext) -> None:
        """Stops the current song and clears the queue. Requires 45% approval. DJs can always stop."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)

        # Check if the user is a DJ
        is_dj: bool = ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]
        if is_dj:
            audio_player.stop()
            await ctx.respond("⏹️ **Stopped**.")
            return

        # Add a vote and check if the player should be stopped
        vote: tuple[int, int, bool] = audio_player.vote(audio_player.stop, ctx.author.id, 0.45)
        if vote[2]:
            await ctx.respond("🗳️ **Voted to stop** the player.")
            return
        percent: int = round(vote[0] / vote[1] * 100)
        await ctx.respond(f"🗳️ **Vote to stop** the player. {vote[0]}/{vote[1]} (**{percent}%**)")

    @slash_command()
    async def queue(
            self,
            ctx: CustomApplicationContext,
            page: Option(
                int,
                "The page to view. Defaults to 1.",
                required=False
            ) = 1
    ) -> None:
        """Displays the current queue."""

        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player:
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        if not len(audio_player):
            await ctx.respond("❌ **The queue is empty**.")
            return

        pages: int = ceil(len(audio_player) / 9)
        if not 1 <= page <= pages:
            await ctx.respond(f"❌ **Page** `{page}` **does not exist**. The queue has **{pages}** pages.")
            return

        start: int = (page - 1) * 9
        end: int = start + 9
        duration: int = audio_player.duration

        description: str = (
            f"**Size:** `{len(audio_player)}`\n"
            f"**Duration:** `{format_time(duration)}`\n"
            "\n"
            "**Currently Playing:**\n"
            f"`{audio_player.current.source.title}` by `{audio_player.current.uploader}`\n"
            "\n"
            "**Requesters:**\n"
        )

        emojis: list[Emoji] = [
            await ctx.bot.database.get_emoji("aubanana"),
            await ctx.bot.database.get_emoji("aublack"),
            await ctx.bot.database.get_emoji("aublue"),
            await ctx.bot.database.get_emoji("aubrown"),
            await ctx.bot.database.get_emoji("augreen"),
            await ctx.bot.database.get_emoji("augrey"),
            await ctx.bot.database.get_emoji("auorange"),
            await ctx.bot.database.get_emoji("aupink"),
            await ctx.bot.database.get_emoji("aupurple"),
            await ctx.bot.database.get_emoji("auyellow"),
            await ctx.bot.database.get_emoji("auwhite"),
            await ctx.bot.database.get_emoji("aucyan"),
            await ctx.bot.database.get_emoji("aumaroon"),
            await ctx.bot.database.get_emoji("aucoral"),
            await ctx.bot.database.get_emoji("aurose"),
            await ctx.bot.database.get_emoji("autan"),
            await ctx.bot.database.get_emoji("aulime"),
            await ctx.bot.database.get_emoji("aured")
        ]
        shuffle(emojis)

        #  requester.mention: emoji
        requesters: dict[str, Emoji] = {}

        embed: Embed = Embed(
            title="Queue",
            description=description,
            color=Color.blurple()
        )

        for i, song in enumerate(audio_player[start:end], start=start + 1):
            if not requesters.get(song.requester.mention):
                requesters[song.requester.mention] = emojis.pop(0)
        for requester, emoji in requesters.items():
            embed.description += f"{emoji} {requester}\n"
        embed.description += "\n**Queue:**\n"

        for i, song in enumerate(audio_player[start:end], start=start + 1):
            url = urlparse(song.source.url)  # used to shorten the url in some cases
            emoji: Emoji = requesters[song.requester.mention]
            embed.description += f"`{i}.` {emoji} [{song.source.title}]({url.scheme}://{url.netloc}{url.path})\n"

        embed.set_footer(text=f"Page {page}/{pages}")
        await ctx.respond(embed=embed)

    @slash_command()
    async def now(self, ctx: CustomApplicationContext) -> None:
        """Displays the currently playing song."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player or not audio_player.current:
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        song: Song = audio_player.current
        message = await ctx.respond(
            embed=song.get_embed(audio_player.loop, list(audio_player[:5]), progress=audio_player.progress)
        )
        audio_player.add_message(await message.original_response())

    @slash_command()
    async def shuffle(self, ctx: CustomApplicationContext) -> None:
        """Shuffles the queue, requires 33% approval. DJs can always shuffle."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player or not len(audio_player):
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        # Check if the user is a DJ
        is_dj: bool = ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]
        if is_dj:
            audio_player.shuffle()
            await ctx.respond("🔀 **Shuffled**.")
            return

        # Add a vote and check if the queue should be shuffled
        vote: tuple[int, int, bool] = audio_player.vote(audio_player.shuffle, ctx.author.id, 0.33)
        if vote[2]:
            await ctx.respond("🗳️ **Voted to shuffle** the queue.")
            return

        percent: int = round(vote[0] / vote[1] * 100)
        await ctx.respond(f"🗳️ **Vote to shuffle** the queue. {vote[0]}/{vote[1]} (**{percent}%**)")

    @slash_command()
    async def history(self, ctx: CustomApplicationContext) -> None:
        """Displays the last 5 songs played."""

        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if audio_player is None:
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        if not audio_player.history:
            await ctx.respond("❌ **No history**.")
            return

        embed: Embed = Embed(
            title="History",
            color=Color.blurple()
        )
        for i, song in enumerate(audio_player.history, start=1):
            embed.add_field(
                name=f"{i}. {song.source.title}",
                value=f"**Duration:** `{format_time(song.duration)}`\n"
                      f"**Requester:** {song.requester.mention}",
                inline=False
            )
        await ctx.respond(embed=embed)

    @slash_command()
    async def clear(self, ctx: CustomApplicationContext) -> None:
        """Clears the queue. Requires 45% approval. DJs can clear without approval."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player or not len(audio_player):
            await ctx.respond("❌ **Not currently playing** anything.")
            return

        if ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]:
            audio_player.clear()
            await ctx.respond("📂 **Cleared** the queue.")
            return

        vote: tuple[int, int, bool] = audio_player.vote(audio_player.clear, ctx.author.id, 0.45)

        if vote[2]:
            await ctx.respond("🗳️ **Voted to clear** the queue.")
            return
        percent: int = round(vote[0] / vote[1] * 100)
        await ctx.respond(f"🗳️ **Vote to clear** the queue. {vote[0]}/{vote[1]} (**{percent}%**)")


def setup(bot: TornadoBot) -> None:
    bot.add_cog(Music(bot))
