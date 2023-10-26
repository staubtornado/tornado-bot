from asyncio import wait_for, TimeoutError, Event, QueueFull, sleep
from collections import deque
from typing import Iterator, Callable

from discord import VoiceClient, HTTPException, Forbidden, Message, FFmpegPCMAudio, InteractionMessage, NotFound, Member

from lib.contexts import CustomApplicationContext
from lib.db.db_classes import Emoji, UserStats
from lib.enums import AudioPlayerLoopMode, SongEmbedSize
from lib.exceptions import NotEnoughVotes
from lib.logging import log, save_traceback
from lib.music.extraction import YTDLSource
from lib.music.queue import SongQueue
from lib.music.song import Song
from lib.spotify.track import Track


class AudioPlayer:
    ctx: CustomApplicationContext

    _queue: SongQueue[Song]
    _message: Message | InteractionMessage | None
    _votes: dict[Callable[[], None], set[int]]

    def __init__(self, ctx: CustomApplicationContext) -> None:
        self.ctx = ctx
        self._queue = SongQueue(maxsize=200)

        self._voice = None
        self._votes = {}
        self._loop = AudioPlayerLoopMode.NONE
        self._timestamp = 0
        self._message = None
        self._current = None
        self._event = Event()
        self._history = deque(maxlen=5)
        self._player_task = self.ctx.bot.loop.create_task(self._player())
        self.embed_size = SongEmbedSize.DEFAULT

        self.ctx.bot.loop.create_task(self._inactivity_check())

    def __del__(self) -> None:
        self._cleanup()

    def __bool__(self) -> bool:
        return self.active

    def __len__(self) -> int:
        return len(self._queue)

    def __iter__(self) -> Iterator[Song]:
        return iter(self._queue)

    def __getitem__(self, item: int | slice) -> SongQueue[Song] | Song:
        if isinstance(item, slice):
            return self._queue[item.start:item.stop:item.step]
        return self._queue[item]

    def __reversed__(self) -> reversed:
        return reversed(self._queue)

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
        Between zero and one
        """
        return ((self.voice.timestamp / 1000 * 0.02) - self._timestamp) / self.current.duration

    @property
    def duration(self) -> int:
        """
        :returns: The duration of the queue in seconds.
        """
        return self._queue.duration

    @property
    def history(self) -> deque[Song]:
        """
        :returns: The last five songs played.
        """
        return self._history

    @property
    def message(self) -> Message | None:
        """
        :return: The last message associated with the newest song embed.
        """
        return self._message

    @message.setter
    def message(self, value: Message | None) -> None:
        """
        Overwriting using this getter will delete the deprecated song embed.
        :param value: The new message.
        :return: None
        """

        if self.message:
            try:
                self.ctx.bot.loop.create_task(self.message.delete())
            except (Forbidden, HTTPException, NotFound):
                pass
        self._message = value

    @property
    def full(self) -> bool:
        """
        Returns True if the queue is full.

        :return: The boolean, true or false.
        """
        return self._queue.full()

    @property
    def live(self) -> bool:
        """
        If the player plays live audio or not.

        :return: True if live audio is played, otherwise False.
        """
        if self.current:
            return self.current.duration > 0
        return False

    async def _inactivity_check(self) -> None:
        """
        Checks if the bot is alone in the voice channel.
        If it is, it will leave directly.

        :return: None
        """

        while True:
            await sleep(60)
            if not self.active:
                break

            member_amount = len([member for member in self.voice.channel.members if not member.bot])
            if not member_amount:
                self._cleanup()

    async def _player(self) -> None:
        self.embed_size = (await self.ctx.bot.database.get_guild_settings(self.ctx.guild.id)).song_embed_size

        while True:
            self._event.clear()

            #  Add the previous song to queue if loop is enabled
            if self.loop and self.current:
                self.reset(self.current)  # Reset the current song, so it can be played again

                try:
                    if self._loop == AudioPlayerLoopMode.QUEUE:
                        self._queue.put_nowait(self.current)
                    else:
                        self._queue.insert(0, self.current)
                except QueueFull:
                    emoji_attention: Emoji = await self.ctx.bot.database.get_emoji("attention")
                    await self.send(f"{emoji_attention} **Queue is full**, ignoring loop.")

            # Add the song to the history
            if self.current and self.current not in self.history:
                self.history.append(self.current)

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

            # Play the song
            self._voice.play(song.source, after=self._prepare_next)
            self._current = song
            self._timestamp = int(self.voice.timestamp / 1000 * 0.02)

            # Send the message
            self.message = await self.send(embed=song.get_embed(
                loop=self.loop,
                queue=list(self._queue),
                size=self.embed_size,
                progress=0
            ))

            for member in self.voice.channel.members:
                if member.bot:
                    continue

                user_stats: UserStats = await self.ctx.bot.database.get_user_stats(member.id)
                user_stats.songs_played += 1
                user_stats.songs_minutes += song.duration
                await self.ctx.bot.database.set_user_stats(user_stats)

            # Process the next song in the queue to minimize the delay
            await self._process_next()
            await self._event.wait()  # Wait for the song to end

    def put(self, song: Song, index: int = None) -> None:
        """
        Put a song in the queue.
        :param song: The song to put in the queue
        :param index: The index to put the song at

        :return: None

        :raises asyncio.QueueFull: If the queue is full
        """

        if index is not None:
            return self._queue.insert(index, song)
        self._queue.put_nowait(song)

    def clear(self) -> None:
        """
        Clear the queue.
        :return: None
        """
        self._queue.clear()

    def skip(self) -> None:
        """
        Skip the current song.
        This disables the loop if it is enabled.
        :return: None
        """
        if self._loop == AudioPlayerLoopMode.SONG:
            self._loop = AudioPlayerLoopMode.NONE

        if self.voice:
            self.voice.stop()

    def back(self) -> None:
        """
        Go back to the previous song.
        :return: None

        :raises asyncio.QueueFull: If the queue is full
        :raises ValueError: If there is no previous song in history
        """
        if not len(self.history):
            raise ValueError("No previous song in history")

        if self._queue.full():
            raise QueueFull("Queue is full.")

        previous: Song = self.history.pop()
        self.reset(previous)  # Reset the stream so the source can be played again
        self.voice.source = previous.source  # Replace the current song with the previous one

        self.reset(self.current)
        self._queue.insert(0, self.current)

        self._timestamp = int(self.voice.timestamp / 1000 * 0.02)  # Update the timestamp
        self._current = previous

        async def _send() -> None:
            message: Message = await self.send(embed=previous.get_embed(
                loop=self.loop,
                queue=list(self._queue),
                size=SongEmbedSize(self.embed_size),
                progress=0
            ))
            self.message = message
        self.ctx.bot.loop.create_task(_send())  # Send the message

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

        :raises IndexError: If the index is out of range
        """
        del self._queue[index]

    def reverse(self) -> None:
        """
        Reverse the queue
        :return: None
        """
        reversed(self._queue)

    def leave(self) -> None:
        self._cleanup()

    def vote(self, func: Callable[[], None], member: Member | int, percentage: float) -> None:
        """
        Vote for a function to execute.

        :param func: The function to vote for.
        :param member: The member who voted. This can be the member id as well.
        :param percentage: The percentage of members needed to execute the function.

        :return: None

        :raises ValueError: If the percentage is not between 0 and 1 or member id is invalid.
        :raises NotEnoughVotes: If there are not enough votes to execute the function.
        """

        if not 0 < percentage <= 1:
            raise ValueError("Percentage must be between 0 and 1")

        if isinstance(member, int):
            member = self.ctx.guild.get_member(member)
            if not member:
                raise ValueError("Invalid member id")

        try:
            self._votes[func].add(member.id)
        except KeyError:
            self._votes[func] = {member.id}

        members: int = len([member for member in self.voice.channel.members if not member.bot])
        if round(len(self._votes[func]) / members, 2) >= percentage:
            func()
            self._votes[func].clear()
            return
        raise NotEnoughVotes(
            f"**Not enough votes** to execute `{func.__name__}`: {len(self._votes[func])}/{members} **(<{percentage})**"
        )

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

    @staticmethod
    def reset(song: Song) -> None:
        """
        Reset a song to its original streaming state.

        :param song: The song to reset
        :return: None
        """
        song.source.original = FFmpegPCMAudio(
            song.source.stream_url, **YTDLSource.FFMPEG_OPTIONS
        )

    def _cleanup(self) -> None:
        self._queue.clear()
        self._player_task.cancel()
        self.message = None

        if self._voice:
            self._voice.stop()
            self.ctx.bot.loop.create_task(self._voice.disconnect())

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
