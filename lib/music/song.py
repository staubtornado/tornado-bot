from typing import Self, Union
from urllib.parse import urlparse

from discord import Member, Embed

from lib.enums import SongEmbedSize, AudioPlayerLoopMode
from lib.music.extraction import YTDLSource
from lib.spotify.track import Track
from lib.utils import format_time, shortened, truncate

HOST_COLORS = {
    "youtube": 0xff0000,
    "soundcloud": 0xff8800,
    "bandcamp": 0x6666ff,
    "vimeo": 0x00ff00,
    "twitch": 0x6441a5,
    "spotify": 0x1db954,
    "attachment": 0x000000,
    "other": 0x000000
}


class Song:
    """
    Class to represent a song

    Attributes
    ----------
    source: YTDLSource
        The source of the song
    requester: Member
        The member who requested the song
    title: str
        The title of the song
    uploader: str
        The uploader of the song
    url: str
        The url of the song
    duration: int
        The duration of the song in seconds
    """

    source: YTDLSource
    requester: Member

    title: str
    uploader: str
    url: str
    duration: int

    def __init__(self, source: Union[YTDLSource, Track], requester: Member = None) -> None:
        if isinstance(source, Track):
            if not requester:
                raise ValueError("Requester must be provided when creating a Song from a Track")

        self._source = source
        self._requester = requester or source.requester

    @property
    def source(self) -> Union[YTDLSource, Track]:
        return self._source

    @property
    def requester(self) -> Member:
        return self._requester

    @property
    def title(self) -> str:
        return self.source.title

    @property
    def uploader(self) -> str:
        return self.source.artist

    @property
    def url(self) -> str:
        return self.source.url

    @property
    def duration(self) -> int:
        return self.source.duration

    def get_embed(
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

        host: str = urlparse(self.source.url).hostname
        embed: Embed = Embed(
            title=self.title,
            color=HOST_COLORS.get(host) or HOST_COLORS["other"]
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
        embed.set_thumbnail(url=self.source.thumbnail_url)

        if size == SongEmbedSize.SMALL:
            return embed

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
        for i, song in enumerate(queue, start=1):
            _queue.append(f"{i}. [{truncate(f'{song.title} by {song.artist}', 55)}]({song.url})")

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
