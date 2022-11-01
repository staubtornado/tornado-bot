from enum import IntEnum
from random import random
from typing import Union, Any, Optional

from discord import Member, Embed

from lib.music.queue import SongQueue
from lib.music.ytdl import YTDLSource
from lib.music.prepared_source import PreparedSource
from lib.utils.utils import time_to_string, shortened


class EmbedSize(IntEnum):
    SMALL = 0  # Only contains description with source, duration Aso...
    NO_QUEUE = 1  # Everything except the queue
    DEFAULT = 2  # Dynamic queue, contains all essential information


class Song:
    source: Union[YTDLSource, PreparedSource]
    requester: Union[Member, Any]  # Will always be Member

    def __init__(self, source: Union[YTDLSource, PreparedSource]) -> None:
        self.source = source
        self.requester = source.requester

    def __str__(self) -> str:
        return str(self.source)

    @staticmethod
    def embed_has_advertisement(embed: Embed) -> bool:
        return len(embed.fields) == 4

    @staticmethod
    def _add_advertisement(embed: Embed) -> Embed:
        if random() <= 0.33:
            embed.add_field(
                name="<a:rooCool:1024373563165249638> Did you know?",
                value=("You can **pause**, **resume**, and **skip songs using** your media **buttons**.\n"
                       "Execute **/**`session` and follow the instructions."),
                inline=False
            )
        return embed

    def to_prepared_src(self):
        """Converts current YTDLSource Object into PreparedSource Object."""

        self.source = PreparedSource(
            self.source.ctx,
            {
                "title": self.source.title,
                "uploader": self.source.uploader,
                "duration": self.source.duration,
                "url": self.source.url
            }
        )

    def create_embed(self, size: EmbedSize, *, queue: SongQueue) -> Embed:
        """Song embed containing all important information related to the song."""

        description: str = (f"[Video]({self.source.url}) **|** [{self.source.uploader}]({self.source.uploader_url}) "
                            f"**|** {time_to_string(self.source.duration)} **|** {self.requester.mention}")

        embed: Embed = Embed(
            title=self.source.title,
            description=description,
            color=0xFF0000
        )
        embed.set_thumbnail(url=self.source.thumbnail_url)

        if size == EmbedSize.SMALL:
            return self._add_advertisement(embed)

        dislikes: Optional[int] = self.source.dislikes
        embed.add_field(name="Views", value=shortened(self.source.views))
        embed.add_field(name="Likes / Dislikes",
                        value=f"{shortened(self.source.likes)} **/** {shortened(dislikes) if dislikes else 'Error'}")
        embed.add_field(name="Uploaded", value=f"<t:{str(self.source.upload_date.timestamp())[:-2]}:R>")

        if size == EmbedSize.NO_QUEUE:
            return self._add_advertisement(embed)

        queue_str: str = ""
        for i, song in enumerate(queue[0:5], start=1):
            queue_str += f"`{i}`. [{song}]({song.source.url})\n"
        if len(queue) > 5:
            remaining: int = len(queue) - queue_str.count("\n")
            queue_str += f"Use **/**`queue` to show **{remaining}** more..."

        embed.add_field(name="Queue", value=queue_str, inline=False) if len(queue) else None
        return self._add_advertisement(embed)
