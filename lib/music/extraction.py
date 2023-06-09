from datetime import datetime
from typing import Self
from urllib.parse import urlparse

from discord import PCMVolumeTransformer, ApplicationContext, FFmpegPCMAudio, Member
from yt_dlp import YoutubeDL

from lib.application_context import CustomApplicationContext
from lib.exceptions import YouTubeNotEnabled


class YTDLSource(PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        # 'quiet': True,
        'source_address': '0.0.0.0',
        'default_search': 'auto'
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    ytdl: YoutubeDL = YoutubeDL(YTDL_OPTIONS)

    ctx: ApplicationContext
    requester: Member

    title: str
    uploader: str
    uploader_url: str
    upload_date: datetime
    url: str
    stream_url: str
    thumbnail_url: str
    views: int
    likes: int
    duration: int

    def __init__(self, ctx: ApplicationContext, source: FFmpegPCMAudio, *, data: dict, volume: float = 0.5) -> None:
        super().__init__(source, volume)

        self._ctx = ctx
        self._requester = ctx.author  # type: ignore

        self._title = data.get('title')
        self._uploader = data.get('uploader')
        self._uploader_url = data.get('uploader_url')
        self._upload_date = datetime.strptime(data.get('upload_date'), '%Y%m%d')
        self._url = data.get('webpage_url')
        self._stream_url = data.get('url')

        try:
            self._thumbnail_url = data.get('thumbnails')[5].get('url')
        except (IndexError, TypeError):
            self._thumbnail_url = data.get('thumbnail')

        self._views = data.get('view_count')
        self._likes = data.get('like_count')
        self._duration = data.get('duration')

    @property
    def ctx(self) -> ApplicationContext:
        return self._ctx

    @property
    def requester(self) -> Member:
        return self._requester  # type: ignore

    @property
    def title(self) -> str:
        return self._title

    @property
    def uploader(self) -> str:
        return self._uploader

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
        return f"{self.title} by {self.uploader}"

    def __repr__(self) -> str:
        return f"<YTDLSource title='{self.title}' uploader='{self.uploader}'>"

    @classmethod
    async def from_url(cls, ctx: CustomApplicationContext, url: str, *, loop=None) -> Self:
        loop = loop or ctx.bot.loop

        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(url, download=False))

        # Check whether URL is from YouTube
        if data['webpage_url_domain'] == 'youtube.com' and not ctx.bot.settings['Music']['YouTubeEnabled']:
            raise YouTubeNotEnabled()

        if 'entries' in data:
            data = data['entries'][0]
        return cls(ctx, FFmpegPCMAudio(data['url'], **cls.FFMPEG_OPTIONS), data=data)

    @classmethod
    async def from_search(cls, ctx: CustomApplicationContext, search: str, *, loop=None) -> Self:
        loop = loop or ctx.bot.loop

        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(search, download=False, process=False))

        if 'entries' in data:
            for entry in data['entries']:
                data = entry
                break
        processed_data = await loop.run_in_executor(
            None,
            lambda: cls.ytdl.extract_info(data['url'], download=False)
        )
        return cls(ctx, FFmpegPCMAudio(processed_data['url'], **cls.FFMPEG_OPTIONS), data=processed_data)
