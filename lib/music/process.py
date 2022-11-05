from asyncio import QueueFull
from typing import Callable, Coroutine, Union, Optional
from urllib.parse import ParseResult

from asyncspotify import BadRequest, SimpleTrack, FullTrack

from lib.music.api import get_track, get_tracks_from_playlist, get_tracks_from_album, get_songs_from_artist
from lib.music.music_application_context import MusicApplicationContext
from lib.music.prepared_source import PreparedSource
from lib.music.song import Song
from lib.music.ytdl import YTDLSource
from lib.utils.utils import url_is_valid, split_list


class AdditionalInputRequiredError(Exception):
    pass


async def process(search: str, ctx: MusicApplicationContext) -> Union[list[Song], Song]:

    url: tuple[bool, ParseResult] = url_is_valid(search)
    res: Optional[Union[list[Union[FullTrack, SimpleTrack, dict, Song]], FullTrack, Song]] = None

    if url[0] and url[1].netloc == "open.spotify.com":
        extractors: dict[str, Callable[[str], Coroutine[str]]] = {
            "track": get_track,
            "playlist": get_tracks_from_playlist,
            "album": get_tracks_from_album,
            "artist": get_songs_from_artist
        }

        try:
            uri: str = url[1].path.split("/")[2]
            res = await extractors.get(url[1].path.split("/")[1])(uri)
        except (KeyError, BadRequest, IndexError):
            raise ValueError("❌ **Invalid** Spotify **link**.")

    # Support for YouTube Music and standard YouTube
    if url[0] and "youtube.com" in url[1].netloc and "playlist" in url[1].path:
        res = await YTDLSource.create_source_playlist(search, loop=ctx.bot.loop)

    if isinstance(res, FullTrack):
        song: Song = Song(PreparedSource(ctx, res))
        try:
            ctx.voice_state.put(song, ctx.playnext)
        except QueueFull:
            raise ValueError("❌ **Queue** is **full**.")
        return song

    remaining: int = ctx.voice_state.queue.maxsize - len(ctx.voice_state.queue)
    if remaining <= 0:
        raise ValueError("❌ **Queue** is **full**.")

    if res and len(res) > remaining:
        message: str = "⚠️ **Playlist is to large** for queue. **What** part do you want **to add**?"

        options: list[str] = []
        for i, part in enumerate(tuple(split_list(res, remaining))[:24]):
            options.append(f"{i * remaining + 1} - {len(part) + (i * remaining)}")
        options.append("Help me choose.")
        raise AdditionalInputRequiredError(message, options, res)

    if res:
        for i in range(len(res)):
            res[i]: Song = Song(PreparedSource(ctx, res[i]))
            ctx.voice_state.put(res[i], ctx.playnext)
        return res

    if search == "https://ffn-stream19.radiohost.de/radiobollerwagen_mp3-192":
        res = Song(PreparedSource(
            ctx,
            {
                "title": "Radio",
                "uploader": "Bollerwagen",
                "duration": -1,
                "url": "https://radiobollerwagen.de/"
            }
        ))
        ctx.voice_state.set_live_stream(search)
        return res
    res = Song(await YTDLSource.create_source(ctx, search, loop=ctx.bot.loop))
    ctx.voice_state.put(res, ctx.playnext)
