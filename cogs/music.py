from math import ceil
from os import environ
from traceback import format_exc

from discord import ApplicationContext, Embed, Bot, slash_command, VoiceChannel, ClientException
from discord.commands.permissions import has_role
from discord.ext.commands import Cog
from discord.utils import get
from psutil import virtual_memory
from spotipy import Spotify, SpotifyClientCredentials, SpotifyException
from yt_dlp import utils

from data.config.settings import SETTINGS
from lib.music.exceptions import YTDLError
from lib.music.extraction import YTDLSource
from lib.music.song import Song
from lib.music.voicestate import VoiceState
from lib.utils.utils import ordinal

utils.bug_reports_message = lambda: ''

sp: Spotify = Spotify(auth_manager=SpotifyClientCredentials(client_id=environ['SPOTIFY_CLIENT_ID'],
                                                            client_secret=environ['SPOTIFY_CLIENT_SECRET']))


def get_track_name(track_id) -> str:
    meta: dict = sp.track(track_id)
    name = meta["name"]
    artist = meta["artists"][0]["name"]
    return f"{name} by {artist}"


def get_playlist_track_names(playlist_id) -> list:
    songs: list = []
    meta: dict = sp.playlist(playlist_id)
    for song in meta['tracks']['items']:
        name = song["track"]["name"]
        artist = song["track"]["artists"][0]["name"]
        songs.append(f"{name} by {artist}")
    return songs


def get_album_track_names(album_id) -> list:
    songs: list = []
    meta: dict = sp.album(album_id)
    for song in meta['tracks']['items']:
        name = song["name"]
        artist = song["artists"][0]["name"]
        songs.append(f"{name} by {artist}")
    return songs


def get_artist_top_songs(artist_id) -> list:
    songs: list = []
    meta: dict = sp.artist_top_tracks(artist_id, country='US')
    for song in meta["tracks"][:10]:
        name = song["name"]
        artist = song["artists"][0]["name"]
        songs.append(f"{name} by {artist}")
    return songs


def ensure_voice_state(ctx):
    if ctx.author.voice is None:
        return "❌ **You are not** connected to a **voice** channel."

    if ctx.voice_client:
        if ctx.voice_client.channel != ctx.author.voice.channel:
            return f"🎶 I am **currently playing** in {ctx.voice_client.channel.mention}."


class CustomApplicationContext(ApplicationContext):
    voice_state: VoiceState


class Music(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: ApplicationContext):
        state = self.voice_states.get(ctx.guild_id)
        if not state or not state.exists:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild_id] = state
        return state

    def cog_unload(self):
        self.check_activity.stop()
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    async def cog_before_invoke(self, ctx: ApplicationContext):
        ctx.voice_state = self.get_voice_state(ctx)

    @slash_command()
    async def join(self, ctx: CustomApplicationContext):
        """Joins a voice channel."""

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        destination: VoiceChannel = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            await ctx.respond(f"👍 **Hello**! Joined {ctx.author.voice.channel.mention}.")
            return

        try:
            ctx.voice_state.voice = await destination.connect()
        except ClientException:
            guild_channel = get(self.bot.voice_clients, guild=ctx.guild)
            if guild_channel == destination:
                pass
            else:
                await guild_channel.disconnect(force=True)
                ctx.voice_state.voice = await destination.connect()
        await ctx.respond(f"👍 **Hello**! Joined {ctx.author.voice.channel.mention}.")

    @slash_command()
    async def clear(self, ctx: CustomApplicationContext):
        """Clears the whole queue."""
        await ctx.defer()

        if ctx.voice_state.processing is False:
            if len(ctx.voice_state.songs) == 0:
                await ctx.respond('❌ The **queue** is **empty**.')
                return
            ctx.voice_state.songs.clear()
            ctx.voice_state.loop = False
            ctx.voice_state.queue_loop = False
            await ctx.respond('🧹 **Cleared** the queue.')
        else:
            await ctx.respond('⚠ I am **currently processing** the previous **request**.')

    @slash_command()
    async def summon(self, ctx: CustomApplicationContext, *, channel: VoiceChannel = None):
        """Summons the bot to a voice channel. If no channel was specified, it joins your channel."""

        if not channel and not ctx.author.voice:
            return await ctx.respond("❌ You are **not in a voice channel** and you **did not specify** a voice "
                                     "channel.")

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()
        await ctx.guild.change_voice_state(channel=destination, self_mute=False, self_deaf=True)
        await ctx.respond(f"👍 **Hello**! Joined {destination.mention}.")

    @slash_command()
    async def leave(self, ctx: CustomApplicationContext):
        """Clears the queue and leaves the voice channel."""
        try:
            await ctx.voice_state.stop()
            voice_channel = get(self.bot.voice_clients, guild=ctx.guild)
            if voice_channel:
                await voice_channel.disconnect(force=True)

            await ctx.respond(f"👋 **Bye**. Left {ctx.author.voice.channel.mention}.")
        except AttributeError:
            await ctx.respond(f"⚙ I am **not connected** to a voice channel so my **voice state has been reset**.")
        del self.voice_states[ctx.guild.id]

    @slash_command()
    async def volume(self, ctx: CustomApplicationContext, *, volume: int):
        """Sets the volume of the current song."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if not ctx.voice_state.is_playing:
            return await ctx.respond("❌ **Nothing** is currently **playing**.")

        if not (0 < volume <= 100):
            return await ctx.respond("❌ The **volume** has to be **between 0 and 100**.")

        if volume < 50:
            emoji: str = "🔈"
        elif volume == 50:
            emoji: str = "🔉"
        else:
            emoji: str = "🔊"

        ctx.voice_state.current.source.volume = volume / 100
        await ctx.respond(f"{emoji} **Volume** of the song **set to {volume}%**.")

    @slash_command()
    async def now(self, ctx: CustomApplicationContext):
        """Displays the currently playing song."""
        await ctx.defer()

        try:
            await ctx.respond(embed=ctx.voice_state.current.create_embed(ctx.voice_state.songs))
        except AttributeError:
            await ctx.respond("❌ **Nothing** is currently **playing**.")

    @slash_command()
    async def pause(self, ctx: CustomApplicationContext):
        """Pauses the currently playing song."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            return await ctx.respond("⏯ **Paused** song, use **/**`resume` to **continue**.")
        await ctx.respond("❌ Either is the **song already paused**, or **nothing is currently **playing**.")

    @slash_command()
    async def resume(self, ctx: CustomApplicationContext):
        """Resumes a currently paused song."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            return await ctx.respond("⏯ **Resumed** song, use **/**`pause` to **pause**.")
        await ctx.respond("❌ Either is the **song is not paused**, or **nothing is currently **playing**.")

    @slash_command()
    async def stop(self, ctx: CustomApplicationContext):
        """Stops playing song and clears the queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if ctx.voice_state.processing is False:
            ctx.voice_state.songs.clear()

            if ctx.voice_state.is_playing:
                ctx.voice_state.voice.stop()
                ctx.voice_state.current = None
                return await ctx.respond("⏹ **Stopped** the player and **cleared** the **queue**.")
            await ctx.respond("❌ **Nothing** is currently **playing**.")
        else:
            await ctx.respond('⚠ I am **currently processing** the previous **request**.')

    @slash_command()
    async def skip(self, ctx: CustomApplicationContext, force: bool = False):
        """Vote to skip a song. The requester can automatically skip."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if not ctx.voice_state.is_playing:
            await ctx.respond("❌ **Nothing** is currently **playing**.")
            return

        loop_note: str = "."
        if ctx.voice_state.queue_loop:
            loop_note: str = " and **removed song from** queue **loop**."

        voter = ctx.author
        if voter == ctx.voice_state.current.requester:
            await ctx.respond(f"⏭ **Skipped** the **song directly**, cause **you** added it{loop_note}")
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            required_votes: int = ceil((len(ctx.author.voice.channel.members) - 1) * (1 / 3))

            if total_votes >= required_votes:
                await ctx.respond(f"⏭ **Skipped song**, as **{total_votes}/{required_votes}** users voted{loop_note}")
                ctx.voice_state.skip()
            else:
                await ctx.respond(f"🗳️ **Skip vote** added: **{total_votes}/{required_votes}**")
        else:
            await ctx.respond("❌ **Cheating** not allowed**!** You **already voted**.")

    @slash_command()
    @has_role("DJ")
    async def forceskip(self, ctx: CustomApplicationContext):
        """Skips a song directly."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if not ctx.voice_state.is_playing:
            return await ctx.respond(f"❌ **Nothing** is currently **playing**.")
        await ctx.respond("⏭ **Forced to skip** current song.")
        ctx.voice_state.skip()

    @slash_command()
    async def queue(self, ctx: CustomApplicationContext, *, page: int = 1):
        """Shows the queue. You can optionally specify the page to show. Each page contains 10 elements."""
        await ctx.defer()

        if len(ctx.voice_state.songs) == 0:
            return await ctx.respond('❌ The **queue** is **empty**.')

        items_per_page = 10
        pages = ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue: str = ""
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += f"`{i + 1}`. [{song.source.title_limited_embed}]({song.source.url})\n"
        duration: int = 0
        for song in ctx.voice_state.songs:
            try:
                duration += int(song.source.data.get("duration"))
            except TypeError:
                continue

        embed: Embed = Embed(title="Queue", description=f"**Songs:** {len(ctx.voice_state.songs)}\n**Duration:** "
                                                        f"{YTDLSource.parse_duration(duration)}\n\n"
                                                        f"**Now Playing:**\n"
                                                        f"[{ctx.voice_state.current.source.title_limited_embed}]"
                                                        f"({ctx.voice_state.current.source.url}) - "
                                                        f"[{ctx.voice_state.current.source.uploader}]"
                                                        f"({ctx.voice_state.current.source.uploader_url}) "
                                                        f"{ctx.voice_state.current.source.duration}\n\n{queue}",
                             colour=0xFF0000)
        embed.set_footer(text=f"Page {page}/{pages}")
        await ctx.respond(embed=embed)

    @slash_command()
    async def shuffle(self, ctx: CustomApplicationContext):
        """Shuffles the queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if len(ctx.voice_state.songs) == 0:
            return await ctx.respond("❌ The **queue** is **empty**.")

        ctx.voice_state.songs.shuffle()
        await ctx.respond("🔀 **Shuffled** the queue.")

    @slash_command()
    async def reverse(self, ctx: CustomApplicationContext):
        """Reverses the queue."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if len(ctx.voice_state.songs) == 0:
            await ctx.respond("❌ The **queue** is **empty**.")
            return
        ctx.voice_state.songs.reverse()
        await ctx.respond("↩ **Reversed** the **queue**.")

    @slash_command()
    async def remove(self, ctx: CustomApplicationContext, index: int):
        """Removes a song from the queue at a given index."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if len(ctx.voice_state.songs) == 0:
            return await ctx.respond("❌ The **queue** is **empty**.")

        try:
            ctx.voice_state.songs.remove(index - 1)
        except IndexError:
            await ctx.respond(f"❌ **No song** has the **{ordinal(n=index)} position** in queue.")
            return
        await ctx.respond(f"🗑 **Removed** the **{ordinal(n=index)} song** in queue.")

    @slash_command()
    async def loop(self, ctx: CustomApplicationContext, queue: bool):
        """Loops the currently playing song or queue. Invoke this command again to disable loop."""
        await ctx.defer()

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if not ctx.voice_state.is_playing:
            return await ctx.respond("❌ **Nothing** is currently **playing**.")

        mode: str = "song, use **/**`loop`"
        if queue is None:
            ctx.voice_state.queue_loop = False
            ctx.voice_state.loop = not ctx.voice_state.loop
        else:
            duration: int = 0
            for song in ctx.voice_state.songs:
                try:
                    duration += int(song.source.data.get("duration"))
                except TypeError:
                    continue

            if duration > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
                await ctx.respond("❌ The **queue is too long** to be looped.")
                return

            ctx.voice_state.loop = False
            ctx.voice_state.queue_loop = queue

            mode: str = "queue, use **/**`loop True`"
            if queue:
                mode: str = "queue, use **/**`loop False`"

        if ctx.voice_state.loop or ctx.voice_state.queue_loop:
            await ctx.respond(f"🔁 **Looped** {mode} to **disable** loop.")
            return
        await ctx.respond(f"🔁 **Unlooped** {mode} to **enable** loop.")

    @slash_command()
    async def play(self, ctx: CustomApplicationContext, *, search: str):
        """Play a song through the bot, by searching a song with the name or by URL."""
        await ctx.defer()

        if ctx.voice_state.processing:
            await ctx.respond("⚠ I am **currently processing** the previous **request**.")
            return

        instance = ensure_voice_state(ctx)
        if isinstance(instance, str):
            await ctx.respond(instance)
            return

        if not ctx.voice_state.voice:
            await self.join(self, ctx)

        if len(ctx.voice_state.songs) >= SETTINGS["Cogs"]["Music"]["MaxQueueLength"]:
            await ctx.respond("🥵 **Too many** songs in queue.")
            return

        if virtual_memory().percent > 75 and SETTINGS["Production"]:
            await ctx.respond("🔥 **I am** currently **experiencing high usage**. Please try again **later**.")
            return

        async def add_song(track_name: str):
            try:
                source = await YTDLSource.create_source(ctx, track_name, loop=self.bot.loop)
            except Exception as error:
                return error

            if not ctx.voice_state.voice:
                await self.join(ctx)

            song = Song(source)
            await ctx.voice_state.songs.put(song)
            return source

        async def process():
            if any(x in search for x in ["https://open.spotify.com/playlist/", "spotify:playlist:",
                                         "https://open.spotify.com/album/", "spotify:album:",
                                         "https://open.spotify.com/track/", "spotify:track:",
                                         "https://open.spotify.com/artist/", "spotify:artist:"]):
                song_names: list = []
                errors: int = 0

                try:
                    if "playlist" in search:
                        song_names.extend(get_playlist_track_names(search))
                    elif "album" in search:
                        song_names.extend(get_album_track_names(search))
                    elif "track" in search:
                        song_names.append(get_track_name(search))
                    elif "artist" in search:
                        song_names.extend(get_artist_top_songs(search))
                    else:
                        raise SpotifyException

                except SpotifyException:
                    await ctx.respond("❌ **Invalid** or **unsupported** Spotify **link**.")
                    return

                for i, song_name in enumerate(song_names):
                    if not len(ctx.voice_state.songs) >= 100:
                        song_process = await add_song(song_name)
                        if isinstance(song_process, Exception):
                            errors += 1
                        continue
                    errors += len(song_names) - i
                    break

                info: str = song_names[0].replace(" by ", "** by **") if len(song_names) == 1 else \
                    f"{len(song_names) - errors} songs"
                await ctx.respond(f":white_check_mark: Added **{info}** from **Spotify**.")
                return

            name = await add_song(search)
            if isinstance(name, YTDLError):
                await ctx.respond(f"❌ {name}")
            elif isinstance(name, utils.GeoRestrictedError):
                await ctx.respond("🌍 This **video** is **not available in** my **country**.")
            elif isinstance(name, utils.UnavailableVideoError):
                await ctx.respond("🚫 This **video is **not available**.")
            elif isinstance(name, Exception):
                traceback = format_exc()
                print(traceback) if traceback is not None else None
                await ctx.respond(f"❌ **Error**: `{name}`")
            else:
                await ctx.respond(f':white_check_mark: Added {name}')

        ctx.voice_state.processing = True
        try:
            await process()
        except Exception as e:
            await ctx.respond(f"**A fatal error has occurred**: `{e}`. **You might** execute **/**`leave` to **reset "
                              f"the voice state on** this **server**.")
        ctx.voice_state.processing = False

    @slash_command()
    async def supported_links(self, ctx):
        """Lists all supported music streaming services."""
        await ctx.respond(embed=Embed(title="Supported Links", description="All supported streaming services.",
                                      colour=0xFF0000)
                          .add_field(name="YouTube", value="✅ Tracks\n❌ Playlists\n❌ Albums\n❌ Artists\n⚠ Livestreams")
                          .add_field(name="YouTube Music", value="✅ Tracks\n❌ Playlists\n❌ Albums\n❌ Artists")
                          .add_field(name="Spotify", value="✅ Tracks\n✅ Playlists\n✅ Albums\n✅ Artists")
                          .add_field(name="Soundcloud", value="✅ Tracks\n❌ Playlists\n❌ Albums\n❌ Artists")
                          .add_field(name="Twitch", value="⚠ Livestreams")
                          .add_field(name="🐞 Troubleshooting", value="If you are experiencing issues, please execute"
                                                                     " **/**`leave`. This should fix most errors.",
                                     inline=False))


def setup(bot):
    bot.add_cog(Music(bot))
