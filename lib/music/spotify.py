from os import environ

from spotipy import Spotify, SpotifyClientCredentials

sp: Spotify = Spotify(auth_manager=SpotifyClientCredentials(client_id=environ['SPOTIFY_CLIENT_ID'],
                                                            client_secret=environ['SPOTIFY_CLIENT_SECRET']))


class SpotifyScraping:

    @staticmethod
    def search(search: str, pattern: str = "track") -> dict:
        return sp.search(q=f"{pattern}:{search}")

    @staticmethod
    def get_track_name(track_id) -> str:
        meta: dict = sp.track(track_id)
        name = meta["name"]
        artist = meta["artists"][0]["name"]
        return f"{name} by {artist}"

    @staticmethod
    def get_playlist_track_names(playlist_id) -> list[str]:
        songs: list = []
        meta: dict = sp.playlist(playlist_id)
        for song in meta['tracks']['items']:
            name = song["track"]["name"]
            artist = song["track"]["artists"][0]["name"]
            songs.append(f"{name} by {artist}")
        return songs

    @staticmethod
    def get_album_track_names(album_id) -> list[str]:
        songs: list = []
        meta: dict = sp.album(album_id)
        for song in meta['tracks']['items']:
            name = song["name"]
            artist = song["artists"][0]["name"]
            songs.append(f"{name} by {artist}")
        return songs

    @staticmethod
    def get_artist_top_songs(artist_id) -> list[str]:
        songs: list = []
        meta: dict = sp.artist_top_tracks(artist_id, country='US')
        for song in meta["tracks"][:10]:
            name = song["name"]
            artist = song["artists"][0]["name"]
            songs.append(f"{name} by {artist}")
        return songs
