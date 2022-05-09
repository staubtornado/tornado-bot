from datetime import datetime

from discord import Embed
from millify import millify

from lib.music.extraction import YTDLSource


class SongStr:
    def __init__(self, search: str, ctx):
        self.search = search
        self.ctx = ctx


class Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    @staticmethod
    def parse_counts(count: int):
        return millify(count, precision=2)

    def create_embed(self, songs):
        description = f"[Video]({self.source.url}) **|** [{self.source.uploader}]({self.source.uploader_url}) **|** " \
                      f"{self.source.duration} **|** {self.requester.mention}"

        date = self.source.upload_date
        timestamp = f"<t:{str(datetime(int(date[6:]), int(date[3:-5]), int(date[:-8])).timestamp())[:-2]}:R>"

        len_songs: int = len(songs)
        queue = ""
        if len_songs == 0:
            pass
        else:
            for i, song in enumerate(songs[0:5], start=0):
                if isinstance(song, Song):
                    queue += f"`{i + 1}.` [{song.source.title_limited_embed}]({song.source.url} '{song.source.title}" \
                             f"')\n"
                else:
                    queue += f"`{i + 1}.` {YTDLSource.parse_limited_title_embed(song.search)}\n"

        if len_songs > 6:
            queue += f"Use **/**`queue` to show **{len_songs - 5}** more..."

        embed = Embed(title=f"🎶 {self.source.title_limited_embed}", description=description, colour=0xFF0000) \
            .add_field(name="Views", value=self.parse_counts(self.source.views), inline=True) \
            .add_field(name="Likes / Dislikes", value=f"{self.parse_counts(self.source.likes)} **/** "
                                                      f"{self.parse_counts(self.source.dislikes)}", inline=True) \
            .add_field(name="Uploaded", value=timestamp, inline=True) \
            .set_thumbnail(url=self.source.thumbnail)
        embed.add_field(name="Queue", value=queue, inline=False) if queue != "" else None
        return embed
