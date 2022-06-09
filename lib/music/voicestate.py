from asyncio import Event, wait_for, shield, TimeoutError

from discord import Bot, FFmpegPCMAudio, Embed, ApplicationContext
from ytmusicapi import YTMusic

from data.config.settings import SETTINGS
from data.db.memory import database
from lib.music.exceptions import VoiceError
from lib.music.extraction import YTDLSource
from lib.music.queue import SongQueue
from lib.music.song import Song, SongStr
from lib.utils.utils import url_is_valid


class VoiceState:
    def __init__(self, bot: Bot, ctx: ApplicationContext):
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
        self.error: int = 0

        self._loop: bool = False
        self._iterate: bool = False
        self._volume: float = 0.5
        self.skip_votes: set = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

        cur = database.cursor()
        cur.execute("""SELECT MusicEmbedSize FROM settings WHERE GuildID = ?""", (self._ctx.guild_id, ))
        self.embed_size = cur.fetchone()[0]
        cur.execute("""SELECT MusicDeleteEmbedAfterSong FROM settings WHERE GuildID = ?""", (self._ctx.guild_id, ))
        self.update_embed = cur.fetchone()[0]

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
                    self.current = await wait_for(shield(self.songs.get()), timeout=180)
                except TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    self.exists = False
                    await self._ctx.send(f"💤 **Bye**. Left {self.voice.channel.mention} due to **inactivity**.")
                    return

                if isinstance(self.current, SongStr):
                    try:
                        try:
                            self.current.source.original = FFmpegPCMAudio(self.current.source.stream_url,
                                                                          **YTDLSource.FFMPEG_OPTIONS)
                            source = self.current.source
                        except AttributeError:
                            response = None
                            search = self.current.get_search()

                            if not url_is_valid(search)[0]:
                                search.replace(":", "")
                                response = f"https://music.youtube.com/watch" \
                                           f"?v={YTMusic().search(search, filter='songs')[0]['videoId']}"
                            source = await YTDLSource.create_source(ctx=self.current.ctx,
                                                                    search=response or search,
                                                                    loop=self.bot.loop)
                    except Exception as error:
                        await self.current.ctx.send(embed=Embed(description=f"💥 **Error**: {error}"))
                        continue
                    else:
                        self.current = Song(source)

                if self.iterate:
                    await self.songs.put(SongStr(self.current, self._ctx))

                    self.loop_duration += int(self.current.source.data.get("duration"))
                    if self.loop_duration > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
                        self.iterate = False

                        await self.current.source.channel.send("🔂 **The queue loop** has been **disabled** due to "
                                                               "**inactivity**.")

                self.current.source.volume = self._volume
                self.voice.play(self.current.source, after=self.play_next_song)

                if self.update_embed:
                    await self.current.source.channel.send(embed=self.current.create_embed(self.songs, self.embed_size),
                                                           delete_after=float(self.current.source.data.get("duration")))
                else:
                    await self.current.source.channel.send(embed=self.current.create_embed(self.songs, self.embed_size))

            elif self.loop:
                if self.loop_duration > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
                    self.loop = False
                    await self.current.source.channel.send("🔂 **The loop** has been **disabled** due to "
                                                           "**inactivity**.")
                else:
                    self.loop_duration += int(self.current.source.data.get("duration"))

                self.now = FFmpegPCMAudio(self.current.source.stream_url, **YTDLSource.FFMPEG_OPTIONS)
                self.voice.play(self.now, after=self.play_next_song)

                if self.update_embed:
                    await self.current.source.channel.send(embed=self.current.create_embed(self.songs, self.embed_size),
                                                           delete_after=float(self.current.source.data.get("duration")))
            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()
        self.skip_votes.clear()

    def skip(self):
        self.skip_votes.clear()
        self.loop = False

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()
        self.loop = False

        if self.voice:
            await self.voice.disconnect()
            self.voice = None
