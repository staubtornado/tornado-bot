from asyncio import get_event_loop
from typing import Self
from urllib.parse import urlparse

from aiohttp import ClientSession
from discord import Member, Embed, Color

from lib.enums import SongEmbedSize, AudioPlayerLoopMode
from lib.music.extraction import YTDLSource
from lib.spotify.track import Track
from lib.utils import dominant_color
from lib.utils import format_time, shortened, truncate


class Song:
    """
    Class to represent a song
    """

    def __init__(self, source: YTDLSource | Track, requester: Member = None) -> None:
        if isinstance(source, Track):
            if not requester:
                raise ValueError("Requester must be provided when creating a Song from a Track")

        self._source = source
        self._requester = requester or source.requester

    @property
    def source(self) -> YTDLSource | Track:
        """
        It is recommended to use the properties of this class instead of this property
        :return: The source of the song.
        """
        return self._source

    @property
    def requester(self) -> Member:
        """
        :return: The member who requested the song.
        """
        return self._requester

    @property
    def title(self) -> str:
        """
        :return: The title of the song.
        """
        return self.source.title

    @property
    def artist(self) -> str:
        """
        :return: The artist of the song.
        """
        return self.source.artist

    @property
    def url(self) -> str:
        """
        :return: The url of the song.
        """
        return self.source.url

    @property
    def duration(self) -> int:
        """
        :return: The duration of the song in seconds.
        """
        return self.source.duration

    async def get_embed(
            self,
            loop: AudioPlayerLoopMode,
            queue: list[Self],
            size: SongEmbedSize = SongEmbedSize.DEFAULT,
            progress: float = 0
    ) -> Embed:
        """
        Get an embed for the song

        :param loop: AudioPlayerLoop
            The loop mode of the player
        :param queue: list[Song]
            The queue of the player.
            It Should contain all songs that are intended to be shown in the embed
        :param size: SongEmbedSize
            The size of the embed
        :param progress: int
            Whether to include the elapsed time in the embed.
            If 0, the elapsed time will not be included
        :return: `discord.Embed`
        """

        _loop = get_event_loop()
        # Read the image bytes of the url
        async with ClientSession() as session:
            async with session.get(self.source.thumbnail_url) as response:
                image_bytes = await response.read()

        embed: Embed = Embed(
            title=self.title,
            color=Color.from_rgb(*await _loop.run_in_executor(None, dominant_color, image_bytes))
        )
        if progress:
            elapsed_time: int = int(self.source.duration * progress)
            duration = f"{format_time(elapsed_time)} **/** {format_time(self.source.duration)}"
        else:
            duration = format_time(self.source.duration)

        description: str = (
            f"[URL]({self.source.url}) **|** [{self.source.artist}]({self.source.uploader_url}) **|** "
            f"{duration} **|** {self.requester.mention}"
        )
        embed.description = description

        if size == SongEmbedSize.SMALL:
            return embed
        embed.set_thumbnail(url=self.source.thumbnail_url)

        try:
            embed.add_field(
                name="Views / Likes",
                value=f"{shortened(self.source.views)} **/** {shortened(self.source.likes)}"
            )
        except TypeError:
            pass

        embed.add_field(
            name="Loop",
            value={0: "Disabled", 1: "Queue", 2: "Song"}[loop.value]
        )
        embed.add_field(
            name="Uploaded",
            value=f"<t:{self.source.upload_date.timestamp():.0f}:R>"
        )

        if not len(queue) or size == SongEmbedSize.NO_QUEUE:
            return embed

        _queue: list[str] = []
        for i, song in enumerate(queue[:5], start=1):
            _url = urlparse(song.url)
            url: str = f"{_url.scheme}://{_url.netloc}{_url.path}"
            try:
                _queue.append(f"{i}. [{truncate(f'{song.title} by {song.uploader}', 55)}]({url})")
            except Exception as e:
                pass

        if len(queue) > 5:
            _queue.append(f"Execute **/**queue to **see {len(queue) - 5} more**.")

        embed.add_field(
            name="Queue",
            value="\n".join(_queue)
        )
        return embed

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Song):
            return NotImplemented
        return self.url == other.url
