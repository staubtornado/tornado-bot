from os import environ
from typing import Union

from lyricsgenius import Genius
from lyricsgenius.types import Song
from asyncspotify import Client, ClientCredentialsFlow, PlaylistTrack, FullAlbum, FullTrack
from spotipy import Spotify, SpotifyClientCredentials

sp: Spotify
auth: ClientCredentialsFlow
genius: Genius


def init_music_api():
    global sp
    global auth
    global genius

    sp = Spotify(auth_manager=SpotifyClientCredentials(client_id=environ['SPOTIFY_CLIENT_ID'],
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


async def get_track_name(track_id: str) -> str:
    async with Client(auth) as asp:
        meta: FullTrack = await asp.get_track(track_id)
    return f"{meta.name} by {meta.artists[0].name}"


async def get_playlist_track_names(playlist_id: str) -> list[str]:
    songs: list[str] = []

    async with Client(auth) as asp:
        meta: list[PlaylistTrack] = await asp.get_playlist_tracks(playlist_id)

    for i in range(len(meta)):
        track: PlaylistTrack = meta[i]
        songs.append(f"{track.name} by {track.artists[0].name}")
    return songs


async def get_album_track_names(album_id: str) -> list[str]:
    tracks: list[str] = []
    async with Client(auth) as asp:
        meta: FullAlbum = await asp.get_album(album_id)
    for track in meta.tracks:
        tracks.append(f"{track.name} by {track.artists[0].name}")
    return tracks


async def get_artist_top_songs(artist_id: str) -> list[str]:
    songs: list[str] = []
    async with Client(auth) as asp:
        meta: list[FullTrack] = await asp.get_artist_top_tracks(artist_id, market='US')
    for entry in meta:
        songs.append(f"{entry.name} by {entry.artists[0].name}")
    return songs


def get_lyrics(song: str, artist: str) -> tuple[str, str, str, str]:
    response: Union[Song, None] = genius.search_song(title=song, artist=artist.replace(" - Topic", ""))
    return response.lyrics, response.song_art_image_url, response.title, response.artist
