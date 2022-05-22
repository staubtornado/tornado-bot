from datetime import datetime
from typing import Union

from discord import Embed

from lib.music.extraction import YTDLSource
from lib.utils.utils import shortened


class SongStr:
    def __init__(self, data: Union[dict, str], ctx):
        self.title = ""
        self.url = None
        self.uploader = None
        self.ctx = ctx

        if isinstance(data, dict):
            self.title = data["title"]
            self.url = data["url"]
            self.uploader = data["uploader"]
            return

        parts = data.split(" by ")
        self.uploader = parts[len(parts) - 1]
        if len(parts) > 2:
            self.title = data.replace(f" by {self.uploader}", "")
            return
        self.title = parts[0]

    def __str__(self):
        if self.url is None:
            return f"{YTDLSource.parse_limited_title_embed(self.title + ' by ' + self.uploader)}"
        return f"[{YTDLSource.parse_limited_title_embed(self.title + ' by ' + self.uploader)}]({self.url})"

    def get_search(self) -> str:
        search = self.url or f"{self.title} by {self.uploader}"
        return search


class Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self, songs, size: int = 2):
        description = f"[Video]({self.source.url}) **|** [{self.source.uploader}]({self.source.uploader_url}) **|** " \
                      f"{self.source.duration} **|** {self.requester.mention}"

        embed = Embed(title=f"🎶 {self.source.title_limited_embed}", description=description, colour=0xFF0000)
        embed.set_thumbnail(url=self.source.thumbnail)

        if size == 0:
            return embed

        embed.add_field(name="Views", value=shortened(self.source.views), inline=True)
        embed.add_field(name="Likes / Dislikes", value=f"{shortened(self.source.likes)} **/** "
                                                       f"{shortened(self.source.dislikes)}", inline=True)

        date = self.source.upload_date
        timestamp = f"<t:{str(datetime(int(date[6:]), int(date[3:-5]), int(date[:-8])).timestamp())[:-2]}:R>"
        embed.add_field(name="Uploaded", value=timestamp, inline=True)

        if size == 1:
            return embed

        len_songs: int = len(songs)
        queue = ""
        if len_songs != 0:
            for i, song in enumerate(songs[0:5], start=0):
                if isinstance(song, Song):
                    queue += f"`{i + 1}.` [{song.source.title_limited_embed}]({song.source.url} '{song.source.title}" \
                             f"')\n"
                else:
                    queue += f"`{i + 1}.` {song}\n"

        if len_songs > 6:
            queue += f"Use **/**`queue` to show **{len_songs - 5}** more..."

        embed.add_field(name="Queue", value=queue, inline=False) if queue != "" else None
        return embed
