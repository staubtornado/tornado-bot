from asyncio import Event, Task, sleep, wait_for, TimeoutError, QueueFull
from enum import IntEnum
from random import randrange
from typing import Optional, Any, Union, Self

from discord import VoiceClient, Guild, Embed, FFmpegPCMAudio, TextChannel, ApplicationContext, Forbidden, User

from bot import CustomBot
from data.config.settings import SETTINGS
from lib.db.data_objects import GuildSettings, EmbedSize, GlobalUserStats
from lib.music.exceptions import YTDLError
from lib.music.prepared_source import PreparedSource
from lib.music.queue import SongQueue
from lib.music.song import Song
from lib.music.ytdl import YTDLSource
from lib.utils.utils import save_traceback


class Loop(IntEnum):
    NONE = 0
    SONG = 1
    QUEUE = 2


class VoiceState:
    bot: CustomBot
    guild: Guild
    _channel: Union[TextChannel, Any]

    processing: bool
    is_valid: bool
    id: str

    current: Optional[Song]
    voice: Optional[VoiceClient]
    queue: SongQueue
    history: list[str]
    live: bool
    position: int
    exception: Optional[Exception]
    _loop: Loop

    session: dict[int, tuple[str, bool]]
    skip_votes: set[int]

    _waiter: Event
    _player: Task
    _checker: Task
    _default_volume: float
    embed_size: int
    update_embed: bool

    def __init__(self, bot: CustomBot, settings: GuildSettings, ctx: ApplicationContext) -> None:
        self.bot = bot
        self.guild = ctx.guild
        self._channel = ctx.channel

        self.processing = False
        self.is_valid = True
        self.id = '{0:010x}'.format(randrange(16**8)).upper()[2:]

        self.current = None
        self.voice = None
        self.queue = SongQueue(maxsize=SETTINGS["Cogs"]["Music"]["Queue"]["MaxQueueLength"])
        self.history = []
        self.live = False
        self.position = 0
        self.exception = None
        self._loop = Loop.NONE

        self.session: dict[int, tuple[str, bool]] = {}
        self.skip_votes: set[int] = set()

        self._waiter = Event()
        self._player = bot.loop.create_task(self._player_task())
        self._checker = bot.loop.create_task(self._inactivity_check())
        self._default_volume = 0.5

        self.embed_size = settings.music_embed_size
        self.update_embed = settings.refresh_music_embed

    def __del__(self) -> None:
        self._player.cancel()
        self._checker.cancel()

    @classmethod
    async def create(cls, bot: CustomBot, ctx: ApplicationContext) -> Self:
        settings: GuildSettings = await bot.database.get_guild_settings(ctx.guild)
        return cls(bot, settings, ctx)

    @property
    def channel(self) -> Optional[Union[TextChannel, Any]]:
        if self.current:
            return self.current.source.channel
        return self._channel

    @property
    def loop(self) -> Loop:
        return self._loop

    @loop.setter
    def loop(self, value: Loop) -> None:
        self._loop = value

    @property
    def volume(self) -> float:
        if isinstance(self.current, Song):
            return self.current.source.volume
        return self._default_volume

    @volume.setter
    def volume(self, value) -> None:
        if isinstance(self.current, Song):
            self.current.source.volume = value

    @property
    def is_playing(self) -> bool:
        return bool(self.voice) and bool(self.current)

    def add_control(self, u_id: int) -> None:
        if u_id in self.session:
            raise ValueError(f"❌ Current **session ID** has **already been send** to you.")

        connections: list[int] = [connection for connection in self.session if self.session[connection][1]]
        if len(connections) >= 3:
            raise ValueError("❌ **Too many** users **are** already **connected**.")
        self.session[u_id] = ('{0:010x}'.format(randrange(16**2)).upper()[8:], False)

    def put(self, song: Song, playnext: bool) -> None:
        if playnext:
            self.queue.insert(0, song)
        else:
            self.queue.put_nowait(song)

    async def send(self, message: str = None, embed: Embed = None, delete_after: float = None) -> None:
        if message is None and embed is None:
            return
        if self.channel:
            try:
                await self.channel.send(content=message, embed=embed, delete_after=delete_after)
            except Forbidden:
                pass

    def set_live_stream(self, stream_url: str) -> None:
        self.queue.clear()
        self.voice.stop()

        self.loop = Loop.NONE
        self.current = None
        self.live = True
        self.voice.play(FFmpegPCMAudio(stream_url, **YTDLSource.FFMPEG_OPTIONS))

    async def _leave(self) -> None:
        self.bot.loop.create_task(self.stop())
        try:
            await self.send(f"💤 **Bye**. Left {self.voice.channel.mention} due to **inactivity**.")
        except (AttributeError, Forbidden):
            pass

    async def _inactivity_check(self) -> None:
        await sleep(30)
        while self.voice is not None and self.voice.is_connected():
            if not [member for member in self.voice.channel.members if not member.bot]:
                break
            await sleep(180)
        if self.is_valid:
            await self._leave()

    async def _player_task(self) -> None:
        while True:
            self._waiter.clear()

            previous: Optional[FFmpegPCMAudio] = None
            if self.current:
                previous: FFmpegPCMAudio = FFmpegPCMAudio(self.current.source.stream_url, **YTDLSource.FFMPEG_OPTIONS)

            if self.loop != Loop.SONG:
                self.current = None

                try:
                    self.current = await wait_for(self.queue.get(), timeout=180)
                except TimeoutError:
                    if self.live:
                        continue

                    if self.is_valid:
                        return await self._leave()
                    return

                if self.loop == Loop.QUEUE:
                    remake: Song

                    if isinstance(self.current.source, PreparedSource):
                        remake = self.current
                    else:
                        remake = Song(PreparedSource(
                            self.current.source.ctx,
                            {
                                "title": self.current.source.title,
                                "uploader": self.current.source.uploader,
                                "duration": self.current.source.duration,
                                "url": self.current.source.url
                            }
                        ))
                    try:
                        self.queue.put_nowait(remake)
                    except QueueFull:
                        pass

            elif self.loop == Loop.SONG:
                if previous:
                    self.voice.play(previous, after=self.prepare_next_song)
                else:
                    self.loop = Loop.NONE
                    continue

            if isinstance(self.current.source, PreparedSource):  # Check if processing has to be done
                try:
                    if self.exception:
                        raise self.exception

                    source: YTDLSource = await wait_for(YTDLSource.create_source(
                        self.current.source.ctx, self.current.source.search, loop=self.bot.loop
                    ), timeout=15)
                except Exception as e:
                    embed: Embed = Embed(title="Error", color=0xFF0000)
                    if isinstance(e, ValueError) or isinstance(e, YTDLError):
                        embed.description = str(e)
                    else:
                        attributes: str = str(vars(self.current.source))
                        await save_traceback(e, attributes)
                        embed.description = f"❌ **Error** while **processing** the **song**:\n```{e}```"
                        embed.set_footer(text="An error report has been sent to the developer.")
                    self.current = None
                    self.exception = None
                    await self.send(embed=embed)
                    continue
                self.current = Song(source)

            if self.loop != Loop.SONG:
                self.history.insert(0, str(self.current))
                if len(self.history) > SETTINGS["Cogs"]["Music"]["History"]["MaxHistoryLength"]:
                    del self.history[-1]

                self.voice.play(self.current.source, after=self.prepare_next_song)
            self.position = int(self.voice.timestamp / 1000 * 0.02)

            await self.send(embed=self.current.create_embed(
                (EmbedSize.SMALL, EmbedSize.NO_QUEUE, EmbedSize.DEFAULT)[self.embed_size],
                queue=self.queue, loop=self.loop),
                delete_after=self.current.source.duration if self.update_embed else None
            )

            for member in self.voice.channel.members:
                if member.bot or member.voice.deaf or member.voice.self_deaf:
                    continue
                user: User = self.bot.get_user(member.id)
                stats: GlobalUserStats = await self.bot.database.get_user_stats(user)
                stats.songs_played += 1
                stats.song_duration += self.current.source.duration
                await self.bot.database.update_user_stats(stats)

            if len(self.queue) and isinstance(self.queue[0].source, PreparedSource):
                try:
                    self.queue[0] = Song(await YTDLSource.create_source(
                        self.queue[0].source.ctx,
                        self.queue[0].source.search,
                        loop=self.bot.loop
                    ))
                except Exception as e:
                    self.exception = e
            await self._waiter.wait()

    def prepare_next_song(self, error=None) -> None:
        if error:
            print(f"[ERROR] An error occurred: {error}")
        self.skip_votes.clear()
        self._waiter.set()

    async def _remove_unheard_seconds(self):
        if self.current is None:
            return
        if isinstance(self.current.source, PreparedSource):
            return

        for member in self.voice.channel.members:
            if member.bot or member.voice.deaf or member.voice.self_deaf:
                continue
            user: User = self.bot.get_user(member.id)
            stats: GlobalUserStats = await self.bot.database.get_user_stats(user)
            stats.songs_played -= 1
            remaining: float = int(self.voice.timestamp / 1000 * 0.02) - self.position
            stats.song_duration -= self.current.source.duration - round(remaining)
            await self.bot.database.update_user_stats(stats)

    async def skip(self) -> None:
        if self.loop == Loop.SONG:
            self.loop = Loop.NONE

        if self.is_playing:
            self.voice.stop()
        await self._remove_unheard_seconds()

    async def stop(self) -> None:
        self.queue.clear()

        self.loop = Loop.NONE
        self.is_valid = False

        if self.voice is not None:
            if self.voice.is_connected():
                await self.voice.disconnect()
            self.voice = None
        await self._remove_unheard_seconds()
