from difflib import SequenceMatcher
from typing import Union
from urllib.parse import ParseResult

from spotipy import SpotifyException

from lib.music.extraction import YTDLSource
from lib.music.song import SongStr, Song
from lib.music.api import get_playlist_track_names, get_track_name, get_album_track_names, get_artist_top_songs
from lib.utils.utils import url_is_valid


async def guess_type(search: str, ctx, loop) -> YTDLSource:
    source = await YTDLSource.create_source(
        ctx, search=f'{search.replace(":", "")} description: "auto-generated by youtube"',
        loop=loop)

    match_source: str = source.title
    if " by " in search:
        match_source += f" {source.uploader.replace(' - Topic', '')}"

    if not SequenceMatcher(None, match_source.lower(), search.replace(":", "").lower()).ratio() > 0.5:
        source = await YTDLSource.create_source(ctx, search=search.replace(":", ""), loop=loop)
    return source


async def process(search: str, ctx, loop, priority: bool = False) -> Union[str, YTDLSource]:
    priority: str = {False: "songs", True: "priority_songs"}[priority]
    search_tracks = []
    output = ""
    url: tuple[bool, ParseResult] = url_is_valid(search)
    if url[0]:
        if url[1].netloc == "open.spotify.com":
            algorithms = {"playlist": get_playlist_track_names, "artist": get_artist_top_songs,
                          "track": get_track_name, "album": get_album_track_names}
            output = "Spotify"

            try:
                search_tracks.extend(algorithms[url[1].path.split("/")[1]](search))
            except (KeyError, SpotifyException):
                return "❌ **Invalid** Spotify **link**."

        elif "youtube.com" in url[1].netloc:
            output = "Youtube"
            url_type = await YTDLSource.check_type(search, loop=loop)
            if url_type in ["playlist", "playlist_alt"]:
                search_tracks.extend(await YTDLSource.create_source_playlist(url_type, search,
                                                                             loop=loop))

    if priority == "priority_songs" and (len(ctx.voice_state.priority_songs) + len(search_tracks)) >= 5:
        return "❌ **Priority Queue** cannot get **larger than 5 songs**."

    for i, track in enumerate(search_tracks):
        if len(ctx.voice_state.priority_songs) + len(ctx.voice_state.songs) < 100:
            await ctx.voice_state.__getattribute__(priority).put(SongStr(track, ctx))
            continue
        return f"❌ **Queue reached its limit in size**, therefore **only {i + 1} songs added** from **{output}**."
    else:
        if len(search_tracks):
            response = f"**{len(search_tracks)} songs**" if len(search_tracks) > 1 \
                else f"**{search_tracks[0].replace(' by ', '** by **')}**"
            return f"✅ Added {response} from **{output}**"

    if not url[0]:
        source = await guess_type(search, ctx, loop)
    else:
        source = await YTDLSource.create_source(ctx, search=search, loop=loop)
    await ctx.voice_state.__getattribute__(priority).put(Song(source))
    return source
