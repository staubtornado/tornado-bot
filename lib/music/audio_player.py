from asyncio import wait_for, TimeoutError, Event, QueueFull, sleep
from math import floor
from typing import Any, Iterator, Callable

from discord import VoiceClient, HTTPException, Forbidden, Message, FFmpegPCMAudio, InteractionMessage

from lib.contexts import CustomApplicationContext
from lib.enums import AudioPlayerLoopMode
from lib.logging import log, save_traceback
from lib.music.extraction import YTDLSource
from lib.music.queue import SongQueue
from lib.music.song import Song
from lib.spotify.track import Track


class AudioPlayer:
    ctx: CustomApplicationContext

    _queue: SongQueue[Song]
    _messages: list[Message | InteractionMessage | None]
    _history: list[Song]
    _votes: dict[Callable[[], None], set[int]]

    def __init__(self, ctx: CustomApplicationContext) -> None:
        self.ctx = ctx
        self._queue = SongQueue()

        self._voice = None
        self._votes = {}
        self._loop = AudioPlayerLoopMode.NONE
        self._timestamp = 0
        self._messages = []
        self._current = None
        self._event = Event()
        self._history = []
        self._player_task = self.ctx.bot.loop.create_task(self._player())
        self.embed_size = 2

        self.ctx.bot.loop.create_task(self._inactivity_check())

    def __del__(self) -> None:
        self._cleanup()

    def __bool__(self) -> bool:
        return self.active

    def __len__(self) -> int:
        return len(self._queue)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._queue)

    def __getitem__(self, item: int | slice) -> SongQueue[Song] | Song:
        if isinstance(item, slice):
            return self._queue[item.start:item.stop:item.step]
        return self._queue[item]

    @property
    def active(self) -> bool:
        """
        Whether the player is active
        :return: True if the player is active, False otherwise
        """
        return self._player_task is not None and not self._player_task.done()

    @property
    def current(self) -> Song | None:
        """
        The current song.
        :return: Song if there is a song playing, None otherwise
        """
        return self._current

    @property
    def voice(self) -> VoiceClient | None:
        """
        The voice client.
        :return: VoiceClient if there is a voice client, None otherwise
        """
        return self._voice

    @voice.setter
    def voice(self, value: VoiceClient | None) -> None:
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
        :returns: The percentage of the current song that has been played.
        Between 0 and 1
        """
        return ((self.voice.timestamp / 1000 * 0.02) - self._timestamp) / self.current.duration

    @property
    def duration(self) -> int:
        """
        :returns: The duration of the queue in seconds.
        """
        return self._queue.duration

    @property
    def history(self) -> list[Song]:
        """
        :returns: The last 5 songs played.
        """
        return self._history

    async def _inactivity_check(self) -> None:
        """
        Checks if the bot is alone in the voice channel.
        If it is, it will leave directly.

        :return: None
        """

        await sleep(60)
        while self.active:
            member_amount = len([member for member in self.voice.channel.members if not member.bot])
            if not member_amount:
                self._cleanup()
            await sleep(60)

    async def _player(self) -> None:
        self.embed_size = (await self.ctx.bot.database.get_guild_settings(self.ctx.guild.id)).song_embed_size

        while True:
            self._event.clear()
            await self._delete_previous_messages()

            #  Add the previous song to queue if loop is enabled
            if self.loop and self.current:
                self.current.source.original = FFmpegPCMAudio(
                    self.current.source.stream_url, **YTDLSource.FFMPEG_OPTIONS
                )

                try:
                    if self._loop == AudioPlayerLoopMode.QUEUE:
                        self._queue.put_nowait(self.current)
                    else:
                        self._queue.insert(0, self.current)
                except QueueFull:
                    await self.send("⚠️ **Queue is full**, ignoring loop.")

            #  Waiting for the next song, leaving if there is no song in 3 minutes
            self._current = None
            try:
                song: Song = await wait_for(self._queue.get(), timeout=180)
            except TimeoutError:
                if self.active:
                    try:
                        await self.send(f"**Left** {self.voice.channel.mention} **due to inactivity**.")
                    except AttributeError:
                        pass
                self._cleanup()
                break

            if not self.active:
                break

            #  Convert the track to a playable source
            if isinstance(song.source, Track):
                try:
                    source = await YTDLSource.from_track(song.requester, song.source, loop=self.ctx.bot.loop)
                except ValueError:
                    continue
                except Exception as e:
                    await save_traceback(e)
                    continue
                song = Song(source)

            # Add the song to the history
            if song not in self._history:
                self._history.append(song)
            self._history = self._history[-5:]

            # Play the song
            self._voice.play(song.source, after=self._prepare_next)
            self._current = song
            self._timestamp = int(self.voice.timestamp / 1000 * 0.02)

            # Send the message
            self._messages.append(await self.send(embed=await song.get_embed(self.loop, list(self._queue), 2, 0)))

            # Process the next song in the queue to minimize the delay
            await self._process_next()
            await self._event.wait()  # Wait for the song to end

    def add_message(self, message: Message | InteractionMessage | None) -> None:
        """
        Add a message to the player
        :param message: The message to add

        :return: None
        """
        self._messages.append(message)

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
        Skip the current song.
        Disable loop of song if it is enabled.
        :return: None
        """
        if self._loop == AudioPlayerLoopMode.SONG:
            self._loop = AudioPlayerLoopMode.NONE

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
        self._loop = AudioPlayerLoopMode.NONE
        if self.voice:
            self.voice.stop()

    def shuffle(self) -> None:
        """
        Shuffle the queue
        :return: None
        """
        self._queue.shuffle()

    def remove(self, index: int) -> None:
        """
        Remove a song from the queue
        :param index: The index of the song to remove

        :return: None
        """
        del self._queue[index]

    def leave(self) -> None:
        self._cleanup()

    def vote(self, func: Callable[[], None], member_id: int, percentage: float = 0.45) -> tuple[int, int, bool]:
        """
        Request a vote to execute a function.
        Executes the function if the vote is successful.

        Example: Clear the queue if 50% of the members vote for it: player.vote(player.clear, ctx.author.id, 0.5)

        :param func: The function to execute, it should not take any positional arguments

        :param member_id: The member who requested the vote.
        :param percentage: The percentage of members required executing the function

        :returns: A tuple containing the number of votes, required votes, and if the vote was successful
        """

        if func not in self._votes:
            self._votes[func] = set()
        self._votes[func].add(member_id)

        votes: int = len(self._votes[func])
        total_members: int = len([member.id for member in self.voice.channel.members if not member.bot])
        required: int = floor(total_members * percentage)

        if votes >= required:
            self._votes[func].clear()
            func()
            return votes, required, True
        return votes, required, False

    async def send(self, *args, **kwargs) -> Message | None:
        """
        Send a message to the channel.
        Note: If the message fails to send, it will be ignored.
        :param args: The arguments to pass to `discord.abc.Messageable.send`
        :param kwargs: The keyword arguments to pass to `discord.abc.Messageable.send`
        :return: None
        """
        try:
            return await self.ctx.send(*args, **kwargs)
        except (Forbidden, HTTPException):
            pass

    def _cleanup(self) -> None:
        self._queue.clear()
        self._player_task.cancel()
        self.ctx.bot.loop.create_task(self._delete_previous_messages())

        if self._voice:
            self._voice.stop()
            self.ctx.bot.loop.create_task(self._voice.disconnect())

    async def _delete_previous_messages(self) -> None:
        for message in self._messages:
            try:
                await message.delete()
            except (Forbidden, HTTPException):
                break
            except AttributeError:
                pass
        self._messages.clear()

    def _prepare_next(self, error=None) -> None:
        if error:
            log(f"Player error: {error}", error=True)
            self.ctx.bot.loop.create_task(save_traceback(error))
        if self.skip in self._votes:
            self._votes[self.skip].clear()
        self._event.set()

    async def _process_next(self) -> None:
        if len(self._queue) and self.loop != AudioPlayerLoopMode.SONG:
            next_song = self._queue[0]
            if isinstance(next_song.source, Track):
                try:
                    source = await YTDLSource.from_track(next_song.requester, next_song.source, loop=self.ctx.bot.loop)
                except ValueError:
                    del self._queue[0]
                except Exception as e:
                    await save_traceback(e)
                    del self._queue[0]
                else:
                    next_song.source = source
