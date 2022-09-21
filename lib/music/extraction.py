from asyncio import get_event_loop
from functools import partial as func_partial
from json import loads
from typing import Union

from discord import PCMVolumeTransformer, ApplicationContext, FFmpegPCMAudio
from requests import get as req_get
from yt_dlp import YoutubeDL

from data.config.settings import SETTINGS
from lib.music.exceptions import YTDLError
from lib.utils.utils import time_to_string


class YTDLSource(PCMVolumeTransformer):
    YTDL_OPTIONS = {
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

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: ApplicationContext, source: FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.user
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get("uploader")
        self.uploader_url = data.get("uploader_url")
        date = data.get('upload_date')
        self.upload_date = f"{date[6:8]}.{date[4:6]}.{date[0:4]}"
        self.title = data.get("title")
        self.title_limited = self.parse_limited_title(self.title)
        self.title_limited_embed = self.parse_limited_title_embed(self.title)
        self.thumbnail = data.get("thumbnail")
        self.duration = self.parse_duration(data.get("duration"))
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count") if data.get("like_count") is not None else -1
        self.stream_url = data.get("url")

        # TEMPORARY DEACTIVATED DUE TO MASSIVE BUGS
        # try:
        #     self.dislikes = int(
        #         dict(loads(req_get(f"https://returnyoutubedislikeapi.com/votes?videoId={data.get('id')}")
        #                    .text))["dislikes"])
        # except KeyError:
        #     self.dislikes = -1
        self.dislikes = -1

    def __str__(self):
        return f"**{self.title_limited}** by **{self.uploader}**"

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop=None):
        loop = loop or get_event_loop()

        partial = func_partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(f"**Could not find anything** that matches `{search}`")

        if "entries" not in data:
            process_info = data
        else:
            process_info = None
            for entry in data["entries"]:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(f"❌ **Could not find anything** that matches `{search}`.")

        webpage_url = process_info["webpage_url"]
        partial = func_partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError(f"❌ **Could not fetch** `{webpage_url}`")

        if "entries" not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info["entries"][0]
                except IndexError:
                    raise YTDLError(f"❌ **Could not retrieve any matches** for `{webpage_url}`")

        if info.get("duration") is None:
            raise YTDLError("❌ **Livestreams are** currently **no longer supported**.")

        if int(info["duration"]) > SETTINGS["Cogs"]["Music"]["MaxDuration"]:
            raise YTDLError("❌ **Songs** can not be **longer than three hours**. Use **/**`loop` to repeat songs.")
        return cls(ctx, FFmpegPCMAudio(info["url"], **cls.FFMPEG_OPTIONS), data=info)

    @classmethod
    async def check_type(cls, search: str, *, loop=None):
        try:
            loop = loop or get_event_loop()

            partial = func_partial(cls.ytdl.extract_info, search, download=False, process=False)
            data = await loop.run_in_executor(None, partial)

            return data["_type"]
        except KeyError:
            pass

    @classmethod
    async def create_source_playlist(cls, typ, search: str, *, loop=None):
        loop = loop or get_event_loop()

        partial = func_partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if typ == 'playlist_alt':
            try:
                search = data["url"]
            except KeyError:
                pass

            partial = func_partial(cls.ytdl.extract_info, search, download=False, process=False)
            data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(f"❌ **Could not retrieve any matches** for `{search}`")
        return [entry for entry in data["entries"] if entry]

    @staticmethod
    def parse_duration(duration: Union[str, int, None]) -> str:
        if duration is None:
            return "LIVE"
        duration: int = int(duration)
        if duration > 0:
            return time_to_string(duration)
        return "Error"

    @staticmethod
    def parse_limited_title(title: str) -> str:
        title = title.replace('||', '')
        return f"{title[:72]}..." if len(title) > 72 else title

    @staticmethod
    def parse_limited_title_embed(title: str) -> str:
        title = title.replace("[", "").replace("]", "").replace("||", "")
        return f"{title[:43]}..." if len(title) > 45 else title
