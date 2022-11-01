from asyncio import Event, Task, sleep, wait_for, TimeoutError, QueueFull
from enum import IntEnum
from random import randrange
from traceback import format_exc
from typing import Optional, Any, Union

from discord import Bot, VoiceClient, Guild, Embed, FFmpegPCMAudio, TextChannel, ApplicationContext

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.music.exceptions import YTDLError
from lib.music.prepared_source import PreparedSource
from lib.music.queue import SongQueue
from lib.music.song import Song, EmbedSize
from lib.music.ytdl import YTDLSource


class Loop(IntEnum):
    NONE = 0
    SONG = 1
    QUEUE = 2


class VoiceState:
    bot: Bot
    guild: Guild
    _channel: Union[TextChannel, Any]

    processing: bool
    is_valid: bool
    id: str

    current: Optional[Song]
    voice: Optional[VoiceClient]
    queue: SongQueue
    history: list[str]
    position: int
    _loop: Loop

    session: dict[int, tuple[str, bool]]
    skip_votes: set[int]

    _waiter: Event
    _player: Task
    _checker: Task
    _default_volume: float
    embed_size: int
    update_embed: bool

    def __init__(self, bot: Bot, ctx: ApplicationContext) -> None:
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
        self.position = 0
        self._loop = Loop.NONE

        self.session: dict[int, tuple[str, bool]] = {}
        self.skip_votes: set[int] = set()

        self._waiter = Event()
        self._player = bot.loop.create_task(self._player_task())
        self._checker = bot.loop.create_task(self._inactivity_check())
        self._default_volume = 0.5

        row: tuple = database.cursor().execute(
            """SELECT MusicEmbedSize, MusicDeleteEmbedAfterSong FROM settings WHERE GuildID = ?""", (self.guild.id, )
        ).fetchone()
        self.embed_size = row[0]
        self.update_embed = bool(row[1])

    def __del__(self) -> None:
        self._player.cancel()
        self._checker.cancel()

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
            await self.channel.send(content=message, embed=embed, delete_after=delete_after)

    async def _leave(self) -> None:
        self.bot.loop.create_task(self.stop())
        try:
            await self.send(f"💤 **Bye**. Left {self.voice.channel.mention} due to **inactivity**.")
        except AttributeError:
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
                    if self.is_valid:
                        return await self._leave()

                if self.loop == Loop.QUEUE:
                    try:
                        self.queue.put_nowait(Song(PreparedSource(
                            self.current.source.ctx,
                            {"title": self.current.source.title,
                             "uploader": self.current.source.uploader,
                             "duration": self.current.source.duration,
                             "url": self.current.source.url}
                        )))
                    except QueueFull:
                        pass

            else:  # Loop.SONG
                if previous:
                    self.voice.play(previous, after=self.prepare_next_song)
                else:
                    self.loop = Loop.NONE

            if isinstance(self.current.source, PreparedSource):  # Check if processing has to be done
                try:
                    source: YTDLSource = await YTDLSource.create_source(
                        self.current.source.ctx, self.current.source.search, loop=self.bot.loop)
                except Exception as e:
                    embed: Embed = Embed(color=0xFF0000).set_author(name="Error")
                    if isinstance(e, ValueError) or isinstance(e, YTDLError):
                        embed.description = str(e)
                    else:
                        print(format_exc())
                        embed.description = f"❌ An **unexpected error** occurred: `{e}`"
                    await self.send(embed=embed)
                    continue
                self.current = Song(source)

            await self.send(embed=self.current.create_embed(
                (EmbedSize.SMALL, EmbedSize.NO_QUEUE, EmbedSize.DEFAULT)[self.embed_size],
                queue=self.queue),
                delete_after=self.current.source.duration if self.update_embed else None
            )

            self.history.insert(0, str(self.current))
            if len(self.history) > SETTINGS["Cogs"]["Music"]["History"]["MaxHistoryLength"]:
                del self.history[-1]

            self.voice.play(self.current.source, after=self.prepare_next_song)
            self.position = int(self.voice.timestamp / 1000 * 0.02)

            await self._waiter.wait()

    def prepare_next_song(self, error=None) -> None:
        if error:
            print(f"[ERROR] An error occurred: {error}")
        self.skip_votes.clear()
        self._waiter.set()

    def skip(self) -> None:
        self.skip_votes.clear()

        if self.loop == Loop.SONG:
            self.loop = Loop.NONE

        if self.is_playing:
            self.voice.stop()

    async def stop(self) -> None:
        self.queue.clear()

        self.loop = Loop.NONE
        self.is_valid = False

        if self.voice is not None and self.voice.is_connected():
            await self.voice.disconnect()
            self.voice = None
