from asyncio import AbstractEventLoop
from datetime import datetime
from re import sub
from typing import Self, Any, AsyncGenerator
from urllib.parse import quote

from discord import PCMVolumeTransformer, FFmpegPCMAudio, Member
from yt_dlp import YoutubeDL

from lib.contexts import CustomApplicationContext
from lib.exceptions import YouTubeNotEnabled
from lib.spotify.track import Track


class YTDLSource(PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'quiet': True,
        'source_address': '0.0.0.0',
        'default_search': 'auto',
        'playlist_items': '1,2,3,4,5'
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    ytdl: YoutubeDL = YoutubeDL(YTDL_OPTIONS)

    def __init__(self, requester: Member, source: FFmpegPCMAudio, *, data: dict, volume: float = 0.5) -> None:
        super().__init__(source, volume)

        self._requester = requester

        self._name = data.get('title')
        self._artist = sub(r" - Topic", "", data.get('uploader'))
        self._uploader_url = data.get('channel_url')
        self._upload_date = datetime.strptime(data.get('upload_date'), '%Y%m%d')
        self._url = data.get('webpage_url')
        self._stream_url = data.get('url')

        try:
            self._thumbnail_url = data.get('thumbnails')[5].get('url')
        except (IndexError, TypeError):
            self._thumbnail_url = data.get('thumbnail')  # Let yt-dl decide

        self._views = data.get('view_count')
        self._likes = data.get('like_count')
        self._duration = data.get('duration')

    @property
    def requester(self) -> Member:
        return self._requester  # type: ignore

    @property
    def name(self) -> str:
        return self._name

    @property
    def artist(self) -> str:
        return self._artist

    @property
    def uploader_url(self) -> str:
        return self._uploader_url

    @property
    def upload_date(self) -> datetime:
        return self._upload_date

    @property
    def url(self) -> str:
        return self._url

    @property
    def stream_url(self) -> str:
        return self._stream_url

    @property
    def thumbnail_url(self) -> str:
        return self._thumbnail_url

    @property
    def views(self) -> int:
        return self._views

    @property
    def likes(self) -> int:
        return self._likes

    @property
    def duration(self) -> int:
        return self._duration

    def __str__(self) -> str:
        return f"{self.name} by {self.artist}"

    def __repr__(self) -> str:
        return f"<YTDLSource title='{self.name}' uploader='{self.artist}'>"

    @classmethod
    async def from_url(cls, ctx: CustomApplicationContext, url: str, loop: AbstractEventLoop) -> Self:
        """
        Creates a YTDLSource from a URL.
        YouTube URLs are checked against the bot settings to see if they are enabled.

        :param ctx: The context of the command.
        :param url: The URL to create the source from.
        :param loop: The event loop to run the YTDLSource creation in.
        :return: The created YTDLSource.
        """
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(url, download=False))

        # Check whether the URL is from YouTube
        if data['webpage_url_domain'] == 'youtube.com' and not ctx.bot.settings['Music']['YouTubeEnabled']:
            raise YouTubeNotEnabled()

        if 'entries' in data:
            data = data['entries'][0]
        return cls(ctx.author, FFmpegPCMAudio(data['url'], **cls.FFMPEG_OPTIONS), data=data)

    @classmethod
    async def from_search(cls, requester: Member, search: str, loop: AbstractEventLoop) -> Self:
        """
        Creates a YTDLSource from a search.

        :param requester: The member who requested the source.
        :param search: The search to create the source from.
        :param loop: The event loop to run the YTDLSource creation in.
        :return: The created YTDLSource.
        """

        search = quote(search)
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(
            f"https://music.youtube.com/search?q={search}#songs",
            download=False,
            process=False
        ))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:  # entries is a generator, so we need to iterate through it
                if entry:
                    process_info = entry
                    break

        if not process_info:
            raise ValueError("No data to process")

        processed_data = await loop.run_in_executor(
            None,
            lambda: cls.ytdl.extract_info(process_info['url'], download=False)
        )
        return cls(requester, FFmpegPCMAudio(processed_data['url'], **cls.FFMPEG_OPTIONS), data=processed_data)

    @classmethod
    async def from_track(cls, requester: Member, track: Track, loop: AbstractEventLoop) -> Self:
        """
        Creates a YTDLSource from a Track, currently only supports Spotify tracks.

        :param requester: The member who requested the source.
        :param track: The track to create the source from.
        :param loop: The event loop to run the YTDLSource creation in.
        :return: The created YTDLSource.
        """

        search: str = f"{track.name} {' '.join(str(artist) for artist in track.artists)}"
        return await cls.from_search(requester, search, loop=loop)

    @classmethod
    async def search(
            cls,
            requester: Member,
            search: str,
            loop: AbstractEventLoop
    ) -> AsyncGenerator[Self, Any]:
        """
        Searches YouTube for a query and yields the results.

        :param requester: The member who requested the search.
        :param search: The query to search for.
        :param loop: The event loop to run the search in.
        :return: The results of the search.
        """

        search = quote(search)
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(
            f"https://music.youtube.com/search?q={search}#songs",
            download=False,
            process=True
        ))

        for entry in data['entries']:
            yield cls(requester, FFmpegPCMAudio(entry['url'], **cls.FFMPEG_OPTIONS), data=entry)
