from asyncio import wait_for, TimeoutError, Event
from typing import Optional

from discord import VoiceClient, HTTPException, Forbidden, Message

from lib.application_context import CustomApplicationContext
from lib.enums import AudioPlayerLoopMode
from lib.logging import log, save_traceback
from lib.music.queue import SongQueue
from lib.music.song import Song


class AudioPlayer:
    ctx: CustomApplicationContext

    active: bool
    current: Optional[Song]
    loop: AudioPlayerLoopMode
    voice: Optional[VoiceClient]

    _queue: SongQueue[Song]
    _message: Optional[Message]

    def __init__(self, ctx: CustomApplicationContext) -> None:
        self.ctx = ctx
        self._queue = SongQueue()

        self._voice = None
        self._loop = AudioPlayerLoopMode.NONE
        self._timestamp = 0
        self._message = None
        self._current = None
        self._event = Event()
        self._player_task = self.ctx.bot.loop.create_task(self._player())

    def __del__(self) -> None:
        self._cleanup()

    def __bool__(self) -> bool:
        return self.active

    def __len__(self) -> int:
        return len(self._queue)

    @property
    def active(self) -> bool:
        """
        Whether the player is active
        :return: True if the player is active, False otherwise
        """
        return self._player_task is not None and not self._player_task.done()

    @property
    def current(self) -> Optional[Song]:
        """
        The current song.
        :return: Song if there is a song playing, None otherwise
        """
        return self._current

    @property
    def voice(self) -> Optional[VoiceClient]:
        """
        The voice client.
        :return: VoiceClient if there is a voice client, None otherwise
        """
        return self._voice

    @voice.setter
    def voice(self, value: Optional[VoiceClient]) -> None:
        self._voice = value

    @property
    def loop(self) -> AudioPlayerLoopMode:
        """
        The loop mode.
        :return: The loop mode
        """
        return self._loop

    @loop.setter
    def loop(self, value: AudioPlayerLoopMode) -> None:
        self._loop = value

    @property
    def progress(self) -> float:
        """
        The progress of the current song.
        :return: The percentage of the current song that has been played. Between 0 and 1
        """
        return (self._timestamp - self.voice.timestamp / 1000 * 0.02) / self.current.duration

    async def _player(self) -> None:
        while True:
            self._event.clear()
            await self._delete_previous_message()

            try:
                song: Song = await wait_for(self._queue.get(), timeout=180)
            except TimeoutError:
                if self.active:
                    try:
                        await self.ctx.send(f"**Left** {self.voice.channel.mention} **due to inactivity**.")
                    except (Forbidden, HTTPException, AttributeError):
                        pass
                self._cleanup()
                break

            if not self.active:
                break

            self._voice.play(song.source, after=self._prepare_next)
            self._current = song
            self._timestamp = int(self.voice.timestamp / 1000 * 0.02)

            try:
                self._message = await self.ctx.send(embed=song.get_embed(self.loop, list(self._queue), 2, 0))
            except (Forbidden, HTTPException):
                pass
            await self._event.wait()

    def put(self, song: Song) -> None:
        """
        Put a song in the queue
        :param song: The song to put in the queue

        :return: None

        :raises asyncio.QueueFull: If the queue is full
        """
        self._queue.put_nowait(song)

    def clear(self) -> None:
        """
        Clear the queue
        :return: None
        """
        self._queue.clear()

    def skip(self) -> None:
        """
        Skip the current song
        :return: None
        """
        if self.voice:
            self.voice.stop()

    def pause(self) -> None:
        """
        Pause the current song
        :return: None
        """
        if self.voice:
            self.voice.pause()

    def resume(self) -> None:
        """
        Resume the current song
        :return: None
        """
        if self.voice:
            self.voice.resume()

    def stop(self) -> None:
        """
        Stop the player and clear the queue
        :return: None
        """
        self._queue.clear()
        if self.voice:
            self.voice.stop()

    def _cleanup(self) -> None:
        self._queue.clear()
        self._player_task.cancel()
        self.ctx.bot.loop.create_task(self._delete_previous_message())

        if self._voice:
            self._voice.stop()
            self.ctx.bot.loop.create_task(self._voice.disconnect())

    async def _delete_previous_message(self) -> None:
        try:
            await self._message.delete()
        except (Forbidden, HTTPException, AttributeError):
            pass

    def _prepare_next(self, error=None) -> None:
        if error:
            log(f"Player error: {error}", error=True)
            self.ctx.bot.loop.create_task(save_traceback(error))
        self._event.set()
