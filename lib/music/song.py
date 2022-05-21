from datetime import datetime

from discord import Embed

from lib.music.extraction import YTDLSource
from lib.utils.utils import shortened


class SongStr:
    def __init__(self, search: str, ctx):
        self.search = search
        self.ctx = ctx


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
                    if "https://" in song.search:
                        title_parts = str(song.search).split("](")
                        title = YTDLSource.parse_limited_title_embed(title_parts[0])
                        queue += f"`{i + 1}.` [{title}]({title_parts[1]}\n"
                    else:
                        queue += f"`{i + 1}.` {YTDLSource.parse_limited_title_embed(song.search)}\n"

        if len_songs > 6:
            queue += f"Use **/**`queue` to show **{len_songs - 5}** more..."

        embed.add_field(name="Queue", value=queue, inline=False) if queue != "" else None
        return embed
