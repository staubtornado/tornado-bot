import audioop
from asyncio import get_event_loop
from datetime import datetime
from difflib import SequenceMatcher
from functools import partial as functools_partial, partial
from itertools import islice
from json import loads
from re import sub
from time import sleep
from typing import Union, Any, Optional

from aiohttp import ClientSession, ClientTimeout
from discord import PCMVolumeTransformer, Member, TextChannel, FFmpegPCMAudio, ApplicationContext
from yt_dlp import YoutubeDL

from data.config.settings import SETTINGS
from lib.music.exceptions import YTDLError
from lib.utils.utils import time_to_string, all_equal


class YTDLSource(PCMVolumeTransformer):
    YTDL_OPTIONS: dict[str, Union[str, bool]] = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': False,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS: dict[str, str] = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl: YoutubeDL = YoutubeDL(YTDL_OPTIONS)

    ctx: ApplicationContext
    requester: Union[Member, Any]  # Will always be Member
    channel: Union[TextChannel, Any]  # Will always be type TextChannel

    uploader: str
    uploader_url: str
    title: str
    upload_date: datetime
    thumbnail_url: str
    elapsed: float
    duration: int
    url: str
    views: int
    likes: int
    dislikes: Optional[int]
    stream_url: str

    def __init__(self, ctx: ApplicationContext, source: FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.ctx = ctx
        self.requester = ctx.author
        self.channel = ctx.channel

        self.uploader = sub(r" - Topic$", "", data.get("uploader"))
        self.uploader_url = data.get("uploader_url")
        self.title = str(data.get("title")).replace("||", "")[:73]
        self.title_embed = sub(r"[\[\]|]", "", str(data.get("title")))[:43]
        self.thumbnail_url = data.get("thumbnail")
        self.duration = data.get("duration")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.stream_url = data.get("url")
        self.upload_date = datetime(int(data.get("upload_date")[:4]),
                                    int(data.get("upload_date")[4:6]),
                                    int(data.get("upload_date")[6:]))
        self.dislikes = data.get("dislikes")
        self.elapsed = 0

    def __str__(self):
        return f"{self.title} by {self.uploader}"

    @classmethod
    async def _search(cls, search: str, *, loop=None) -> dict:
        loop = loop or get_event_loop()

        def generate_partial(query: str) -> partial:
            return functools_partial(
                cls.ytdl.extract_info,
                query,
                download=False,
                process=False
            )

        data = await loop.run_in_executor(None, generate_partial(
            f'https://www.youtube.com/results?search_query={search} description: "auto-generated by youtube"'
        ))
        music_results: tuple = tuple(islice(data["entries"], 3))

        ranking: dict[int, int] = {}
        for i in range(len(music_results)):
            ranking[i] = 0
        ranking[0] += 1  # First result of search

        highest_views: list[int] = [None, 0]
        highest_match: list[Union[int, float]] = [None, 0]
        for i in range(len(music_results)):
            result: dict = music_results[i]
            ratio: float = SequenceMatcher(None, search, f"{result['title']} {result['uploader']}").ratio()

            if result.get("view_count") > highest_views[1]:
                highest_views[0] = i
                highest_views[1] = result.get("view_count")
            if ratio > highest_match[1]:
                highest_match[0] = i
                highest_match[1] = ratio
        ranking[highest_views[0]] += 1  # Point for highest view count
        ranking[highest_match[0]] += 1  # Point for highest match

        if all_equal(ranking):
            return music_results[highest_views[0]]
        return music_results[max(ranking, key=ranking.get)]

    @classmethod
    async def create_source(cls, ctx: ApplicationContext, search: str, *, loop=None):
        loop = loop or get_event_loop()

        data: dict = await cls._search(search)
        if SequenceMatcher(None, f"{data.get('title')} {data.get('uploader')}", search).ratio() < 0.5:
            part: partial = functools_partial(cls.ytdl.extract_info, search, download=False, process=False)
            data = await loop.run_in_executor(None, part)

        if data is None:
            raise YTDLError(f"❌ **Could not find anything** that matches `{search}`")

        if "entries" not in data:
            process_info = data
        else:
            process_info = None
            for entry in data["entries"]:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(f"❌ **Could not find anything** that matches `{search}`")

        webpage_url = process_info["url"]
        part: partial = functools_partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, part)

        if processed_info is None:
            raise YTDLError(f"❌ **Could not fetch**: `{webpage_url}`")

        if "entries" not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info["entries"][0]
                except IndexError:
                    raise YTDLError(f"❌ **Could not retrieve** any matches for: `{webpage_url}`")

        if info.get("duration") is None:
            raise YTDLError("❌ **Livestreams are** currently **not supported**.")

        if int(info["duration"]) > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
            duration: str = time_to_string(SETTINGS['Cogs']['Music']['MaxDuration'])
            raise YTDLError(f"❌ Songs cannot be longer than **{duration}**.")

        async with ClientSession(timeout=ClientTimeout(total=3)) as session:
            async with session.get(f"https://returnyoutubedislikeapi.com/votes?videoId={info['id']}") as resp:
                info["dislikes"] = dict(loads(await resp.text()))["dislikes"]

        return cls(ctx, FFmpegPCMAudio(info["url"], **cls.FFMPEG_OPTIONS), data=info)

    @classmethod
    async def create_source_playlist(cls, search: str, loop=None) -> list[dict]:
        loop = loop or get_event_loop()
        part: partial = functools_partial(cls.ytdl.extract_info, search, download=False, process=False)

        data: dict = await loop.run_in_executor(None, part)
        if data is None or data.get("_type") is None:
            raise ValueError(f"❌ **Cannot extract** information from `{search}`.")

        if data.get("_type") == "playlist_alt":
            if data.get("url") is not None:
                part: partial = functools_partial(cls.ytdl.extract_info, data["url"], download=False, process=False)
                data = await loop.run_in_executor(None, part)
        return [entry for entry in data["entries"] if entry is not None]
