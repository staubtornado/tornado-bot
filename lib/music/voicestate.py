from asyncio import Event

from _asyncio import Task
from async_timeout import timeout
from discord import Bot, FFmpegPCMAudio

from data.config.settings import SETTINGS
from lib.music.exceptions import VoiceError
from lib.music.extraction import YTDLSource
from lib.music.queue import SongQueue
from lib.music.song import Song


class VoiceState:
    def __init__(self, bot: Bot, ctx):
        self.bot = bot
        self._ctx = ctx

        self.processing: bool = False
        self.now = None
        self.current = None
        self.voice = None
        self.next: Event = Event()
        self.songs: SongQueue = SongQueue()
        self.exists: bool = True
        self.loop_duration: int = 0

        self._loop: bool = False
        self._iterate: bool = False
        self._volume: float = 0.5
        self.skip_votes: set = set()

        self.audio_player: Task = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._iterate = False
        self.loop_duration = 0

        self._loop = value

    @property
    def iterate(self):
        return self._iterate

    @iterate.setter
    def iterate(self, value: bool):
        self._loop = False
        self.loop_duration = 0

        self._iterate = value

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
                    await self.current.source.channel.send(f"💤 **Bye**. Left {self.voice.channel.mention} due to "
                                                           f"**inactivity**.")
                    return

                if self.iterate:
                    source = await YTDLSource.create_source(self._ctx, self.current.source.url, loop=self.bot.loop)
                    await self.songs.put(Song(source))

                    self.loop_duration += int(self.current.source.data.get("duration"))
                    if self.loop_duration > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
                        self.iterate = False

                        await self.current.source.channel.send("🔂 **The queue loop** has been **disabled** due to "
                                                               "**inactivity**.")

                self.current.source.volume = self._volume
                self.voice.play(self.current.source, after=self.play_next_song)
                await self.current.source.channel.send(embed=self.current.create_embed(self.songs))

            elif self.loop:
                if self.loop_duration > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
                    self.loop = False
                    await self.current.source.channel.send("🔂 **The loop** has been **disabled** due to "
                                                           "**inactivity**.")
                else:
                    self.loop_duration += self.current.source.duration

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
        self.loop = False

        if self.voice:
            await self.voice.disconnect()
            self.voice = None
