from asyncio import QueueFull
from math import floor, ceil
from random import shuffle
from re import match
from typing import Optional, Callable
from urllib.parse import urlparse, ParseResultBytes

from discord import Member, VoiceState, VoiceClient, slash_command, Option, VoiceChannel, Embed, Color, \
    InteractionResponded, ClientException
from discord.ext.commands import Cog
from yt_dlp import DownloadError

from bot import TornadoBot
from lib.contexts import CustomApplicationContext
from lib.db.db_classes import Emoji
from lib.exceptions import YouTubeNotEnabled
from lib.logging import save_traceback
from lib.music.audio_player import AudioPlayer
from lib.music.auto_complete import complete
from lib.music.embeds import YOUTUBE_NOT_ENABLED
from lib.music.extraction import YTDLSource
from lib.music.song import Song
from lib.music.views import QueueFill
from lib.spotify.data import SpotifyData
from lib.spotify.exceptions import SpotifyNotFound, SpotifyRateLimit, SpotifyException
from lib.utils import format_time


class Music(Cog):
    _audio_player: dict[int, AudioPlayer]

    def __init__(self, bot: TornadoBot) -> None:
        self.bot = bot
        self._audio_player = {}

    def __getitem__(self, item: int) -> AudioPlayer:
        return self._audio_player[item]

    async def _check_for_valid_player(self, ctx: CustomApplicationContext) -> bool:
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player:
            audio_player = AudioPlayer(ctx)
            self._audio_player[ctx.guild.id] = audio_player

        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")

        # Join a voice channel if not already in one
        if not ctx.author.voice:
            await ctx.respond(f"{emoji_cross} You are **not connected to a voice channel**.")
            return False

        if not audio_player.voice:
            await self.join(ctx)
        return True

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        if member.id != self.bot.user.id:
            return
        if before.channel == after.channel:
            return

        player: Optional[AudioPlayer] = self._audio_player.get(member.guild.id)
        voice_client: VoiceClient = member.guild.voice_client  # type: ignore

        if not after.channel:
            if player:
                player.voice = None
            return

        if before.channel is None and after.channel is not None:
            pass

        if player:
            player.voice = voice_client

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
        """Joins a voice channel."""

        if not self._audio_player.get(ctx.guild.id):
            self._audio_player[ctx.guild.id] = AudioPlayer(ctx)
        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")  # Get the cross-emoji

        if destination := destination or ctx.author.voice.channel:
            try:
                await destination.connect()
            except ClientException:
                await ctx.respond(f"{emoji_cross} I am **already connected to a voice channel**.")
                return

            emoji_checkmark2: Emoji = await self.bot.database.get_emoji("checkmark2")
            await ctx.respond(f"{emoji_checkmark2} **Hello**! **Joined** {destination.mention}.")
            return
        await ctx.respond(f"{emoji_cross} You are **not connected to a voice channel**.")

    @slash_command()
    async def leave(self, ctx: CustomApplicationContext) -> None:
        """Leaves a voice channel, requires 50% approval. DJ permissions override this."""

        # If the bot is not connected to a voice channel
        if not ctx.guild.voice_client:
            emoji_cross: Emoji = await self.bot.database.get_emoji("cross")
            await ctx.respond(f"{emoji_cross} I am **not connected to a voice channel**.")
            return

        emoji_checkmark2: Emoji = await self.bot.database.get_emoji("checkmark2")

        # Check if the user is a DJ
        is_dj: bool = ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]
        if is_dj:
            await ctx.guild.voice_client.disconnect(force=False)
            del self._audio_player[ctx.guild.id]
            await ctx.respond(f"{emoji_checkmark2} **Goodbye**!")
            return

        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)

        # Add a vote to leave and check if the vote was successful
        vote: tuple[int, int, bool] = audio_player.vote(audio_player.leave, ctx.author.id, 0.5)
        if vote[2]:
            await ctx.guild.voice_client.disconnect(force=False)
            del self._audio_player[ctx.guild.id]
            await ctx.respond(f"{emoji_checkmark2} **Goodbye**!")
            return
        percent: int = floor((vote[0] / vote[1]) * 100)
        await ctx.respond(f"🗳️ **Vote to stop** the player. {vote[0]}/{vote[1]} (**{percent}%**)")

    @slash_command()
    async def play(
            self,
            ctx: CustomApplicationContext,
            search: Option(
                str,
                "The song to play. This can be a search query or a link to a playlist.",
                required=True,
                autocomplete=complete
            )):
        """Plays a song or playlist."""
        try:
            await ctx.defer()
        except InteractionResponded:
            pass

        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")

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
                await ctx.respond(f"{emoji_cross} **Invalid** Spotify **URL**.")
                return
            except SpotifyException as e:
                await ctx.respond(f"{emoji_cross} **Spotify** API **error**.")
                if isinstance(e, SpotifyRateLimit):
                    return
                return await save_traceback(e)
        elif parse_result.scheme in ("http", "https"):  # If the search query is another URL
            try:
                result = await YTDLSource.from_url(ctx, search, loop=self.bot.loop)
            except YouTubeNotEnabled:
                await ctx.respond(embed=YOUTUBE_NOT_ENABLED)
                return
            except DownloadError:
                await ctx.respond(f"{emoji_cross} **Download error**. Try a different source.")
                return
        else:  # If the search query is a search query
            if match(r"Playlist: .+", search):
                playlist_suggestions: list[SpotifyData] = await ctx.bot.spotify.get_trending_playlists()

                for playlist in playlist_suggestions:
                    if search[10:] == playlist.name:
                        return await self.play(ctx, playlist.url)
            try:
                result = await YTDLSource.from_search(
                    ctx.author,
                    search,
                    loop=self.bot.loop
                )
            except ValueError:
                await ctx.respond(f"{emoji_cross} **No results**.")
                return

        # Check for valid existing player
        if not await self._check_for_valid_player(ctx):
            return
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)

        emoji_playlist: Emoji = await ctx.bot.database.get_emoji("playlist")
        emoji_checkmark: Emoji = await ctx.bot.database.get_emoji("checkmark")

        # Check if the result is iterable, if not, it is a single song
        try:
            iter(result)
        except TypeError:
            audio_player.put(Song(result, ctx.author))
            await ctx.respond(f"{emoji_checkmark} **Added** `{result.name}` **to the queue**.")
            return

        # If the result is a playlist, add all songs to the queue
        # Check if the playlist is too long for the queue

        if max(len(result), result.total) > 100 - len(audio_player):
            view: QueueFill = QueueFill(ctx, result, audio_player)

            emoji_attention: Emoji = await ctx.bot.database.get_emoji("attention")
            response = await ctx.respond(
                f"{emoji_attention} Playlist **too long** for the queue. **Select** the songs you want to **add**.",
                view=view
            )
            await view.wait()

            if not view.value:
                emoji_cross: Emoji = await ctx.bot.database.get_emoji("cross")
                await response.edit(
                    content=f'{emoji_cross} You **took too long** to respond.',
                    view=None
                )
                return

            try:
                start, stop = view.value.split(" - ")
            except ValueError:
                tracks = await ctx.bot.spotify.get_playlist_tracks(result.id, len(result), result.total)
                result.tracks.extend(tracks)
                shuffle(result.tracks)
                result.tracks = result.tracks[:200 - len(audio_player)]
            else:
                start, stop = int(start) - 1, int(stop)

                result.tracks = result[start:stop]
                tracks = await ctx.bot.spotify.get_playlist_tracks(result.id, start + len(result), stop)
                result.tracks.extend(tracks)

        for track in result:
            audio_player.put(Song(track, ctx.author))
        await ctx.respond(f"{emoji_playlist} **Added** `{len(result)}` **tracks to the queue**.")
        return

    @slash_command()
    async def playnext(
            self,
            ctx: CustomApplicationContext,
            search: Option(
                str,
                "The song to play. This can be a search query or a link.",
                required=True,
                autocomplete=complete
            )):
        """Plays a song next."""

        try:
            await ctx.defer()
        except InteractionResponded:
            pass

        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")

        #  Analyze the search query
        parse_result: ParseResultBytes = urlparse(search)
        if parse_result.netloc == "open.spotify.com":  # If the search query is not a Spotify URL
            if not match(r"(https://)?open.spotify\.com/(intl-\w+/)?track/(\w+)", search):
                await ctx.respond(
                    f"{emoji_cross} **Invalid** Spotify **URL**. **Only tracks** are supported **in this command**."
                )
                return
            try:
                result = await ctx.bot.spotify.get_track(search)
            except SpotifyNotFound:
                await ctx.respond(f"{emoji_cross} **Invalid** Spotify **URL**.")
                return
            except SpotifyException as e:
                await ctx.respond(f"{emoji_cross} **Spotify** API **error**.")
                if isinstance(e, SpotifyRateLimit):
                    return
                return await save_traceback(e)

        elif parse_result.scheme in ("http", "https"):  # If the search query is another URL
            try:
                result = await YTDLSource.from_url(ctx, search, loop=self.bot.loop)
            except YouTubeNotEnabled:
                await ctx.respond(embed=YOUTUBE_NOT_ENABLED)
                return
            except DownloadError:
                await ctx.respond(f"{emoji_cross} **Download error**. Try a different source.")
                return
        else:  # If the search query is a search query
            try:
                result = await YTDLSource.from_search(
                    ctx.author,
                    search,
                    loop=self.bot.loop
                )
            except ValueError:
                await ctx.respond(f"{emoji_cross} **No results**.")
                return

        # Check for valid existing player
        if not await self._check_for_valid_player(ctx):
            return
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)

        emoji_checkmark: Emoji = await ctx.bot.database.get_emoji("checkmark")
        audio_player.put(Song(result, ctx.author), index=0)
        await ctx.respond(f"{emoji_checkmark} **Added** `{result.name}` **to the queue**.")

    @slash_command()
    async def pause(self, ctx: CustomApplicationContext) -> None:
        """Pauses the currently playing song."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")

        if not audio_player:
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return

        if audio_player.voice.is_paused():
            await ctx.respond(f"{emoji_cross} **Already paused**.")
            return
        audio_player.voice.pause()
        emoji_pause: Emoji = await ctx.bot.database.get_emoji("pause")
        await ctx.respond(f"{emoji_pause} **Paused**.")

    @slash_command()
    async def resume(self, ctx: CustomApplicationContext) -> None:
        """Resumes the currently paused song."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")

        if not audio_player:
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return

        if not audio_player.voice.is_paused():
            await ctx.respond(f"{emoji_cross} **Already playing**.")
            return
        audio_player.voice.resume()
        emoji_play: Emoji = await ctx.bot.database.get_emoji("play")
        await ctx.respond(f"{emoji_play} **Resumed**.")

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
        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")

        if not audio_player or not audio_player.current:
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return

        emoji_skip: Emoji = await ctx.bot.database.get_emoji("skip")

        # Check if the user is the requester
        if ctx.author.id == audio_player.current.requester.id:
            audio_player.skip()
            await ctx.respond(f"{emoji_skip} **Skipped**.")
            return

        # Check if the user is a DJ and force skip
        is_dj: bool = ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]
        if force == "True":
            if not is_dj:
                await ctx.respond(f"{emoji_cross} You are **not a DJ**.")
                return
            audio_player.skip()
            await ctx.respond(f"{emoji_skip} **Force skipped**.")
            return

        # Add a vote and check if the song should be skipped
        vote: tuple[int, int, bool] = audio_player.vote(audio_player.skip, ctx.author.id, 0.33)
        if vote[2]:
            await ctx.respond("🗳️ **Voted to skip** the song.")
            return
        percent: int = round(vote[0] / vote[1] * 100)
        await ctx.respond(f"🗳️ **Vote to skip** the song. {vote[0]}/{vote[1]} (**{percent}%**)")

    @slash_command()
    async def previous(self, ctx: CustomApplicationContext) -> None:
        """Plays the previous song."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")

        if not audio_player:
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return

        try:
            audio_player.back()
        except QueueFull:
            await ctx.respond(f"{emoji_cross} **Queue is full.**")
            return
        except ValueError:
            await ctx.respond(f"{emoji_cross} **No previous song.**")
            return

        emoji_back: Emoji = await ctx.bot.database.get_emoji("back")
        await ctx.respond(f"{emoji_back} **Playing previous** song.")

    @slash_command()
    async def stop(self, ctx: CustomApplicationContext) -> None:
        """Stops the current song and clears the queue. Requires 45% approval. DJs can always stop."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)

        # Check if the user is a DJ
        is_dj: bool = ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]
        if is_dj:
            audio_player.stop()
            emoji_stop: Emoji = await ctx.bot.database.get_emoji("stop")
            await ctx.respond(f"{emoji_stop} **Stopped**.")
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
        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")
        if not audio_player:
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return

        if not len(audio_player):
            await ctx.respond(f"{emoji_cross} **The queue is empty**.")
            return

        pages: int = ceil(len(audio_player) / 9)
        if not 1 <= page <= pages:
            await ctx.respond(f"{emoji_cross} **Page** `{page}` **does not exist**. The queue has **{pages}** pages.")
            return

        start: int = (page - 1) * 9
        end: int = start + 9
        duration: int = audio_player.duration

        description: str = (
            f"**Size:** `{len(audio_player)}`\n"
            f"**Duration:** `{format_time(duration)}`\n"
            "\n"
            "**Currently Playing:**\n"
            f"`{audio_player.current.title}` by `{audio_player.current.artist}`\n"
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
            url = urlparse(song.url)  # used to shorten the url in some cases
            emoji: Emoji = requesters[song.requester.mention]
            embed.description += f"`{i}.` {emoji} [{song.title}]({url.scheme}://{url.netloc}{url.path})\n"

        embed.set_footer(text=f"Page {page}/{pages}")
        await ctx.respond(embed=embed)

    @slash_command()
    async def now(self, ctx: CustomApplicationContext) -> None:
        """Displays the currently playing song."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player or not audio_player.current:
            emoji_cross: Emoji = await self.bot.database.get_emoji("cross")
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return

        song: Song = audio_player.current
        message = await ctx.respond(
            embed=song.get_embed(audio_player.loop, list(audio_player), progress=audio_player.progress)
        )
        audio_player.add_message(await message.original_response())

    @slash_command()
    async def shuffle(self, ctx: CustomApplicationContext) -> None:
        """Shuffles the queue, requires 33% approval. DJs can always shuffle."""

        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        if not audio_player:
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return
        if not len(audio_player):
            await ctx.respond(f"{emoji_cross} **The queue is empty**.")
            return

        emoji_shuffle: Emoji = await self.bot.database.get_emoji("shuffle")

        # Check if the user is a DJ
        is_dj: bool = ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]
        if is_dj:
            audio_player.shuffle()
            await ctx.respond(f"{emoji_shuffle} **Shuffled**.")
            return

        # Add a vote and check if the queue should be shuffled
        vote: tuple[int, int, bool] = audio_player.vote(audio_player.shuffle, ctx.author.id, 0.33)
        if vote[2]:
            await ctx.respond(f"{emoji_shuffle} **Voted to shuffle** the queue.")
            return

        percent: int = round(vote[0] / vote[1] * 100)
        await ctx.respond(f"🗳️ **Vote to shuffle** the queue. {vote[0]}/{vote[1]} (**{percent}%**)")

    @slash_command()
    async def history(self, ctx: CustomApplicationContext) -> None:
        """Displays the last 5 songs played."""

        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")
        if audio_player is None:
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return

        if not audio_player.history:
            await ctx.respond(f"{emoji_cross} **No history**.")
            return

        embed: Embed = Embed(
            title="History",
            color=Color.blurple()
        )
        for i, song in enumerate(audio_player.history, start=1):
            embed.add_field(
                name=f"{i}. {song.source.name}",
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
            emoji_cross: Emoji = await self.bot.database.get_emoji("cross")
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return

        if ctx.author.guild_permissions.manage_guild or "DJ" in [role.name for role in ctx.author.roles]:
            emoji_clear: Emoji = await self.bot.database.get_emoji("playlist_clear")
            audio_player.clear()
            await ctx.respond(f"{emoji_clear} **Cleared** the queue.")
            return

        vote: tuple[int, int, bool] = audio_player.vote(audio_player.clear, ctx.author.id, 0.45)

        if vote[2]:
            await ctx.respond("🗳️ **Voted to clear** the queue.")
            return
        percent: int = round(vote[0] / vote[1] * 100)
        await ctx.respond(f"🗳️ **Vote to clear** the queue. {vote[0]}/{vote[1]} (**{percent}%**)")

    @slash_command()
    async def remove(
            self,
            ctx: CustomApplicationContext,
            index: Option(int, "The index of the song to remove.", min_value=1, max_value=200)
    ) -> None:
        """Removes a song from the queue."""
        audio_player: AudioPlayer = self._audio_player.get(ctx.guild.id)
        emoji_cross: Emoji = await self.bot.database.get_emoji("cross")
        if not audio_player or not len(audio_player):
            await ctx.respond(f"{emoji_cross} **Not currently playing** anything.")
            return

        if index > len(audio_player):
            await ctx.respond(f"{emoji_cross} **Invalid index**.")
            return

        song: Song = audio_player[index - 1]
        audio_player.remove(index - 1)
        emoji_checkmark: Emoji = await ctx.bot.database.get_emoji("checkmark")
        await ctx.respond(f"{emoji_checkmark} **Removed** `{song.source.name}` from the queue.")


def setup(bot: TornadoBot) -> None:
    bot.add_cog(Music(bot))
