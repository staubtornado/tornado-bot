from asyncio import get_event_loop, Queue, Event, sleep
from functools import partial as func_partial
from datetime import datetime
from itertools import islice
from math import ceil
from os import environ
from random import shuffle
from time import gmtime, strftime
from requests import get as req_get
from json import loads

from async_timeout import timeout
from discord import PCMVolumeTransformer, ApplicationContext, FFmpegPCMAudio, Embed, Bot, slash_command, VoiceChannel, \
    ClientException
from discord.ext.commands import Cog
from discord.ext.tasks import loop as task_loop
from discord.utils import get
from millify import millify
from spotipy import Spotify, SpotifyClientCredentials, SpotifyException
from urllib3.exceptions import HTTPError, HTTPWarning
from youtube_dl import utils, YoutubeDL

# from ..data.config import settings

utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


sp: Spotify = Spotify(auth_manager=SpotifyClientCredentials(client_id=environ['SPOTIFY_CLIENT_ID'],
                                                            client_secret=environ['SPOTIFY_CLIENT_SECRET']))


def get_track_id(track):
    track = sp.track(track)
    return track["id"]


def get_playlist_track_ids(playlist_id):
    ids = []
    playlist = sp.playlist(playlist_id)
    for item in playlist['tracks']['items']:
        track = item['track']
        ids.append(track['id'])
    return ids


def get_album(album_id):
    album = sp.album_tracks(album_id)
    ids = []
    for item in album['items']:
        ids.append(item["id"])
    return ids


def get_track_features(track_id):
    meta = sp.track(track_id)
    name = meta['name']
    artist = meta['album']['artists'][0]['name']
    return f"{name} - {artist}"


def get_album_id(album_name):
    return sp.album(album_name)


def get_artist_top_songs(artist_id):
    return sp.artist_top_tracks(artist_id, country='US')


def get_artist(artist_id):
    return sp.artist(artist_id)['name']


class YTDLSource(PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': False,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0',
        "cookiefile": "cookies.txt",
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: ApplicationContext, source: FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.user
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get("uploader")
        self.uploader_url = data.get("uploader_url")
        date = data.get('upload_date')
        self.upload_date = f"{date[6:8]}.{date[4:6]}.{date[0:4]}"
        self.title = data.get("title")
        self.title_limited = self.parse_limited_title(self.title)
        self.title_limited_embed = self.parse_limited_title_embed(self.title)
        self.thumbnail = data.get("thumbnail")
        self.description = data.get("description")
        self.duration = self.parse_duration(int(data.get("duration")))
        self.tags = data.get("tags")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.dislikes = int(dict(loads(req_get(f"https://returnyoutubedislikeapi.com/votes?videoId={data.get('id')}")
                                       .text))["dislikes"])
        self.stream_url = data.get("url")

    def __str__(self):
        return f"**{self.title_limited}** by **{self.uploader}**"

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop=None):
        loop = loop or get_event_loop()

        partial = func_partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(f"Could not find anything that matches `{search}`")

        if "entries" not in data:
            process_info = data
        else:
            process_info = None
            for entry in data["entries"]:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(f"Could not find anything that matches `{search}`")

        webpage_url = process_info["webpage_url"]
        partial = func_partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError(f"Could not fetch `{webpage_url}`")

        if "entries" not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info["entries"].pop(0)
                except IndexError:
                    raise YTDLError(f"Could not retrieve any matches for `{webpage_url}`")

        return cls(ctx, FFmpegPCMAudio(info["url"], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        if duration > 0:
            if not duration >= 3600:
                value = strftime('%M:%S', gmtime(duration))
            else:
                value = strftime('%H:%M:%S', gmtime(duration))

        elif duration == 0:
            value = "LIVE"
        else:
            value = "Error"

        return value

    @staticmethod
    def parse_limited_title(title: str):
        title = title.replace('||', '')
        if len(title) > 72:
            return title[:72] + '...'
        else:
            return title

    @staticmethod
    def parse_limited_title_embed(title: str):
        title = title.replace('[', '')
        title = title.replace(']', '')
        title = title.replace('||', '')

        if len(title) > 45:
            return title[:43] + '...'
        else:
            return title


class Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    @staticmethod
    def parse_counts(count: int):
        return millify(count, precision=2)

    def create_embed(self, songs):
        description = f"[Video]({self.source.url}) | [{self.source.uploader}]({self.source.uploader_url}) | " \
                      f"{self.source.duration} | {self.requester.mention}"

        date = self.source.upload_date
        timestamp = f"<t:{str(datetime(int(date[6:]), int(date[3:-5]), int(date[:-8])).timestamp())[:-2]}:R>"

        len_songs: int = len(songs)
        queue = ""
        if len_songs == 0:
            pass
        else:
            for i, song in enumerate(songs[0:5], start=0):
                queue += f"`{i + 1}.` [{song.source.title_limited_embed}]({song.source.url} '{song.source.title}')\n"

        if len_songs > 6:
            queue += f'And **{len_songs - 5}** more...'

        embed = Embed(title=f"🎶 {self.source.title_limited_embed}", description=description, colour=0xFF0000) \
            .add_field(name="Views", value=self.parse_counts(self.source.views), inline=True) \
            .add_field(name="Likes / Dislikes", value=f"{self.parse_counts(self.source.likes)} / "
                                                      f"{self.parse_counts(self.source.dislikes)}", inline=True) \
            .add_field(name="Uploaded", value=timestamp, inline=True) \
            .set_thumbnail(url=self.source.thumbnail)
        embed.add_field(name="Queue", value=queue, inline=False) if queue != "" else None
        return embed


class SongQueue(Queue):
    _queue = None

    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot, ctx):
        self.bot = bot
        self._ctx = ctx

        self.text_channel = ctx.channel
        self.processing = False
        self.now = None
        self.current = None
        self.voice = None
        self.next = Event()
        self.songs = SongQueue()
        self.exists = True

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()
            self.now = None

            if not self.loop:
                try:
                    async with timeout(180):
                        self.current = await self.songs.get()
                except TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    self.exists = False
                    return

                self.current.source.volume = self._volume
                self.voice.play(self.current.source, after=self.play_next_song)
                await self.current.source.channel.send(embed=self.current.create_embed(self.songs))

            elif self.loop:
                self.now = FFmpegPCMAudio(self.current.source.stream_url, **YTDLSource.FFMPEG_OPTIONS)
                self.voice.play(self.now, after=self.play_next_song)

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()
        self.skip_votes.clear()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


async def ensure_voice_state(ctx):
    if ctx.author.voice is None:
        return "❌ **You are not** connected to a **voice** channel."

    if ctx.voice_client:
        if ctx.voice_client.channel != ctx.author.voice.channel:
            return f"🎶 I am **currently playing** in {ctx.voice_client.channel.mention}."


class Music(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.voice_states = {}
        self.check_activity.start()

    @task_loop(seconds=10.0)
    async def check_activity(self):
        await self.bot.wait_until_ready()

        for key in self.voice_states:
            state = self.voice_states[key]

            try:
                channel = await self.bot.fetch_channel(state.voice.channel.id)
            except AttributeError:
                await state.stop()
                del self.voice_states[key]
                return

            if len(channel.members) <= 1:
                await sleep(180)
                if len(channel.members) <= 1:
                    await state.text_channel.send(f"💤 **Bye**. Left {channel.mention} due to **inactivity**.")

                    await state.stop()
                    del self.voice_states[key]
                    return

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
    async def join(self, ctx):
        """Joins a voice channel."""

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            await ctx.respond(f"🤟 **Hello**! Joined {ctx.author.voice.channel.mention}.")
            return

        try:
            ctx.voice_state.voice = await destination.connect()
        except ClientException:
            await get(self.bot.voice_clients, guild=ctx.guild).disconnect(force=True)
            ctx.voice_state.voice = await destination.connect()

        await ctx.respond(f"🤟 **Hello**! Joined {ctx.author.voice.channel.mention}.")

    @slash_command()
    async def clear(self, ctx):
        """Clears the whole queue."""
        await ctx.defer()

        if ctx.voice_state.processing is False:
            if len(ctx.voice_state.songs) == 0:
                await ctx.respond('❌ The **queue** is **empty**.')
                return
            ctx.voice_state.songs.clear()
            await ctx.respond('🧹 **Cleared** the queue.')
        else:
            await ctx.respond('⚠ I am **currently processing** the previous **request**.')

    @slash_command()
    async def summon(self, ctx, *, channel: VoiceChannel = None):
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
        await ctx.respond(f"🤘 **Hello**! Joined {destination.mention}.")

    @slash_command()
    async def leave(self, ctx):
        """Clears the queue and leaves the voice channel."""
        try:
            await ctx.voice_state.stop()
            del self.voice_states[ctx.guild.id]

            voice_channel = get(self.bot.voice_clients, guild=ctx.guild)
            if voice_channel:
                await voice_channel.disconnect(force=True)

            await ctx.respond(f"👋 **Bye**. Left {ctx.author.voice.channel.mention}.")
        except AttributeError:
            await ctx.respond(f"⚙ I am **not connected** to a voice channel so my **voice state has been reset**.")

    @slash_command()
    async def volume(self, ctx, *, volume: int):
        """Sets the volume of the current song."""
        await ctx.defer()

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if not ctx.voice_state.is_playing:
            return await ctx.respond("❌ **Nothing** is currently **playing**.")

        if not (0 < volume <= 100):
            return await ctx.respond("❌ The **volume** has to be **between 0 and 100**.")

        ctx.voice_state.current.source.volume = volume / 100
        await ctx.respond(f"🔊 **Volume** of the player **set to {volume}**.")

    @slash_command()
    async def now(self, ctx):
        """Displays the currently playing song."""
        await ctx.defer()

        try:
            await ctx.respond(embed=ctx.voice_state.current.create_embed(ctx.voice_state.songs))
        except AttributeError:
            await ctx.respond("❌ **Nothing** is currently **playing**.")

    @slash_command()
    async def pause(self, ctx):
        """Pauses the currently playing song."""
        await ctx.defer()

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            return await ctx.respond("⏯ **Paused** song, use **/**`resume` to **continue**.")
        await ctx.respond("❌ Either is the **song already paused**, or **nothing is currently **playing**.")

    @slash_command()
    async def resume(self, ctx):
        """Resumes a currently paused song."""
        await ctx.defer()

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            return await ctx.respond("⏯ **Resumed** song, use **/**`pause` to **pause**.")
        await ctx.respond("❌ Either is the **song is not paused**, or **nothing is currently **playing**.")

    @slash_command()
    async def stop(self, ctx):
        """Stops playing song and clears the queue."""
        await ctx.defer()

        instance = await ensure_voice_state(ctx)
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
    async def skip(self, ctx):
        """Vote to skip a song. The requester can automatically skip. """
        await ctx.defer()

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if not ctx.voice_state.is_playing:
            return await ctx.respond("❌ **Nothing** is currently **playing**.")

        voter = ctx.author
        if voter == ctx.voice_state.current.requester:
            await ctx.respond("⏭ **Skipped song** directly, as **you** added it.")
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            required_votes: int = ceil((len(ctx.author.voice.channel.members) - 1) * (1 / 3))

            if total_votes >= required_votes:
                await ctx.respond(f"⏭ **Skipped song**, as **{total_votes}/{required_votes}** users voted.")
                ctx.voice_state.skip()
            else:
                await ctx.respond(f"🗳️ **Skip vote** added: **{total_votes}/{required_votes}**")
        else:
            await ctx.respond("❌ **Cheating** not allowed**!** You **already voted**.")

    @slash_command()
    async def forceskip(self, ctx):
        """Skips a song directly."""
        await ctx.defer()

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if not ctx.voice_state.is_playing:
            return await ctx.respond(f"❌ **Nothing** is currently **playing**.")
        await ctx.respond("⏭ **Forced to skip** current song.")
        ctx.voice_state.skip()

    @slash_command()
    async def queue(self, ctx, *, page: int = 1):
        """Shows the queue. You can optionally specify the page to show. Each page contains 10 elements."""

        await ctx.defer()
        if len(ctx.voice_state.songs) == 0:
            return await ctx.respond('❌ The **queue** is **empty**.')

        items_per_page = 10
        pages = ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += f"`{i + 1}`. [{song.source.title_limited_embed}]({song.source.url})\n"
        len_queue: int = len(ctx.voice_state.songs)

        embed = Embed(title="Queue", description=f"**Songs:** {len_queue}\n**Estimated length:** "
                                                 f"{YTDLSource.parse_duration(len_queue * 210)}\n\n{queue}",
                      colour=0xFF0000)

        embed.set_footer(text=f"Page {page}/{pages}")
        await ctx.respond(embed=embed)

    @slash_command()
    async def shuffle(self, ctx):
        """Shuffles the queue."""
        await ctx.defer()

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if len(ctx.voice_state.songs) == 0:
            return await ctx.respond('❌ The **queue** is **empty**.')

        ctx.voice_state.songs.shuffle()
        await ctx.respond("🔀 **Shuffled** the queue.")

    @slash_command()
    async def remove(self, ctx, index: int):
        """Removes a song from the queue at a given index."""
        await ctx.defer()

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if len(ctx.voice_state.songs) == 0:
            return await ctx.respond('❌ The **queue** is **empty**.')
        try:
            ctx.voice_state.songs.remove(index - 1)
        except IndexError:
            await ctx.respond(f"❌ **No song** in the queue **at** the given **index {index}**.")
            return
        await ctx.respond(f"🗑 **Removed song** with index **{index}** from queue.")

    @slash_command()
    async def loop(self, ctx):
        """Loops the currently playing song. Invoke this command again to disable loop the song."""
        await ctx.defer()

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if not ctx.voice_state.is_playing:
            return await ctx.respond('❌ **Nothing** is currently **playing**.')

        ctx.voice_state.loop = not ctx.voice_state.loop

        if ctx.voice_state.loop:
            await ctx.respond("🔁 **Looped** song, use **/**`loop` to **disable** loop.")
        else:
            await ctx.respond("🔁 **Unlooped** song, use **/**`loop` to **enable** loop.")

    @slash_command()
    async def play(self, ctx, *, search: str):
        """Play a song through the bot, by searching a song with the name or by URL."""
        await ctx.defer()

        if ctx.voice_state.processing:
            await ctx.respond("⚠ I am **currently processing** the previous **request**.")
            return

        instance = await ensure_voice_state(ctx)
        if isinstance(instance, str):
            return await ctx.respond(instance)

        if not ctx.voice_state.voice:
            await self.join(self, ctx)

        async def create_ytdl_source(track_name: str):
            try:
                source = await YTDLSource.create_source(ctx, track_name, loop=self.bot.loop)
            except errors as error:
                return error

            if not ctx.voice_state.voice:
                await self.join(self, ctx)

            song = Song(source)
            await ctx.voice_state.songs.put(song)
            return source

        if len(ctx.voice_state.songs) >= 100:
            return await ctx.respond("🥵 **Too many** songs in queue.")
        song_ids: list = []

        errors: tuple = (utils.ExtractorError, utils.DownloadError, utils.compat_HTTPError, utils.GeoRestrictedError,
                         utils.UnavailableVideoError, utils.XAttrUnavailableError, utils.YoutubeDLError, HTTPError,
                         HTTPWarning)

        async def analyze_link():
            try:
                if "https://open.spotify.com/playlist/" in search or "spotify:playlist:" in search:
                    song_ids.extend(get_playlist_track_ids(search))

                elif "https://open.spotify.com/album/" in search or "spotify:album:" in search:
                    song_ids.extend(get_album(search))

                elif "https://open.spotify.com/track/" in search or "spotify:track:" in search:
                    track = get_track_features(search)

                    source = await create_ytdl_source(track)
                    if isinstance(source, errors):
                        source = str(source).replace("\n", " ")
                        return await ctx.respond(f"❌ **An error occurred**: `{source}`")
                    return await ctx.respond(f":white_check_mark: Added: **{track}** from **Spotify**.")

                elif 'https://open.spotify.com/artist/' in search or 'spotify:artist:' in search:
                    for result in get_artist_top_songs(search)['tracks'][:10]:
                        song_ids.append(result["id"])
                else:
                    source = await create_ytdl_source(search)
                    if isinstance(source, errors):
                        source = str(source).replace("\n", " ")
                        return await ctx.respond(f"❌ **An error occurred**: `{source}`")
                    return await ctx.respond(f':white_check_mark: Added: {source}')

            except SpotifyException:
                return await ctx.respond("❌ **Invalid** Spotify **link**.")

            if len(ctx.voice_state.songs) + len(song_ids) >= 100:
                return await ctx.respond("🥵 **Too many** songs in queue.")

            failed_songs: int = 0
            for song_id in song_ids:
                source = await create_ytdl_source(get_track_features(song_id))
                if isinstance(source, errors):
                    print(source)
                    failed_songs += 1
                    continue
            await ctx.respond(f":white_check_mark: Added: **{len(song_ids) - failed_songs}** songs from **Spotify**.")

        ctx.voice_state.processing = True
        try:
            await analyze_link()
        except Exception as e:
            print(e)
            e = str(e).replace("\n", " ")
            await ctx.respond(f"❌ **An error occurred**: `{e}`")
        ctx.voice_state.processing = False


def setup(bot):
    bot.add_cog(Music(bot))
