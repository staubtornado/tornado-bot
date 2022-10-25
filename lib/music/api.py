from os import environ
from re import sub
from typing import Optional, Union

from asyncspotify import ClientCredentialsFlow, FullTrack, Client, SimpleTrack
from asyncspotify.client import get_id
from asyncspotify.pager import Pager
from lyricsgenius import Genius
from lyricsgenius.song import Song
from spotipy import Spotify, SpotifyClientCredentials

sp: Optional[Spotify] = None
auth: Optional[ClientCredentialsFlow] = None
genius: Optional[Genius] = None


class FixedAsyncSpotifyClient(Client):
    """
    Fixes TypeError: asyncspotify.http.Route() got multiple values for keyword argument 'limit' for album track
    extraction.
    """

    async def get_album_tracks(self, album, limit=20, offset=None, market=None) -> list[SimpleTrack]:
        """Visit source for documentation. Limit is disabled and set to 50."""

        data = await self.http.get_album_tracks(get_id(album), offset=offset, market=market)
        tracks = []
        async for track_obj in Pager(self.http, data, limit):
            tracks.append(SimpleTrack(self, track_obj))
        return tracks


def init() -> None:
    global sp
    global auth
    global genius

    sp = Spotify(auth_manager=SpotifyClientCredentials(
        client_id=environ['SPOTIFY_CLIENT_ID'],
        client_secret=environ['SPOTIFY_CLIENT_SECRET']))
    auth = ClientCredentialsFlow(
        client_id=environ['SPOTIFY_CLIENT_ID'],
        client_secret=environ['SPOTIFY_CLIENT_SECRET']
    )
    genius = Genius(environ["LYRICS_FIND_ACCESS_TOKEN"])


def search_on_spotify(search: str, pattern: str = "track,artist") -> tuple[list[str], list[str]]:
    response = sp.search(q=search, type=pattern)
    rtrn = [], []

    for result in response["tracks"]["items"]:
        rtrn[0].append(f"{result['name']} by {result['artists'][0]['name']}")
    for result in response["artists"]["items"]:
        rtrn[1].append(f"{result['name']}")
    return rtrn


async def get_track(track_id: str) -> FullTrack:
    async with Client(auth) as async_sp:
        return await async_sp.get_track(track_id)


async def get_tracks_from_playlist(playlist_id: str) -> list[FullTrack]:
    async with Client(auth) as async_sp:
        return await async_sp.get_playlist_tracks(playlist_id)


async def get_tracks_from_album(album_id: str) -> list[SimpleTrack]:
    async with FixedAsyncSpotifyClient(auth) as async_sp:
        return await async_sp.get_album_tracks(album=album_id)


async def get_songs_from_artist(artist_id: str) -> list[FullTrack]:
    async with Client(auth) as async_sp:
        return await async_sp.get_artist_top_tracks(artist_id, market="US")


def get_lyrics(song: str, artist: str) -> tuple[str, str, str, str]:
    response: Union[Song, None] = genius.search_song(title=song, artist=artist.replace(" - Topic", ""))
    response.lyrics = sub(r"(\d*Embed|You might also like)$", "", response.lyrics)
    return response.lyrics, response.song_art_image_url, response.title, response.artist


if not all([sp, auth, genius]):
    init()
