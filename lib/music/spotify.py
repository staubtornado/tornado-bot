from os import environ

from spotipy import Spotify, SpotifyClientCredentials

sp: Spotify = Spotify(auth_manager=SpotifyClientCredentials(client_id=environ['SPOTIFY_CLIENT_ID'],
                                                            client_secret=environ['SPOTIFY_CLIENT_SECRET']))


def search_on_spotify(search: str, pattern: str = "track,artist") -> tuple[list[str], list[str]]:
    response = sp.search(q=search, type=pattern)
    rtrn = [], []

    for result in response["tracks"]["items"]:
        rtrn[0].append(f"{result['name']} by {result['artists'][0]['name']}")
    for result in response["artists"]["items"]:
        rtrn[1].append(f"{result['name']}")
    return rtrn


def get_track_name(track_id) -> list[str]:
    meta: dict = sp.track(track_id)
    name = meta["name"]
    artist = meta["artists"][0]["name"]
    return [f"{name} by {artist}"]


def get_playlist_track_names(playlist_id) -> list[str]:
    songs: list = []
    meta: dict = sp.playlist(playlist_id)
    for song in meta['tracks']['items']:
        name = song["track"]["name"]
        artist = song["track"]["artists"][0]["name"]
        songs.append(f"{name} by {artist}")
    return songs


def get_album_track_names(album_id) -> list[str]:
    songs: list = []
    meta: dict = sp.album(album_id)
    for song in meta['tracks']['items']:
        name = song["name"]
        artist = song["artists"][0]["name"]
        songs.append(f"{name} by {artist}")
    return songs


def get_artist_top_songs(artist_id) -> list[str]:
    songs: list = []
    meta: dict = sp.artist_top_tracks(artist_id, country='US')
    for song in meta["tracks"][:10]:
        name = song["name"]
        artist = song["artists"][0]["name"]
        songs.append(f"{name} by {artist}")
    return songs
