from re import match

from aiohttp import ClientSession

from lib.spotify.album import Album
from lib.spotify.artist import Artist
from lib.spotify.playlist import Playlist
from lib.spotify.track import Track


class SpotifyAPI:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = None

    async def _get_token(self) -> None:
        async with ClientSession() as session:
            async with session.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret
                }
            ) as response:
                data = await response.json()
                self._token = data["access_token"]

    @staticmethod
    def _strip_url(url: str) -> str:
        m = match(r"(https://)?open.spotify\.com/(intl-\w+/)?(track|album|artist|playlist)/(\w+)", url)
        if m:
            return m.group(4)
        raise ValueError("Invalid Spotify URL")

    async def _get(self, url: str) -> dict:
        if not self._token:
            await self._get_token()
        async with ClientSession() as session:
            async with session.get(
                url,
                headers={
                    "Authorization": f"Bearer {self._token}"
                }
            ) as response:
                return await response.json()

    async def get_track(self, track_id: str) -> Track:
        response: dict = await self._get(f"https://api.spotify.com/v1/tracks/{track_id}")
        return Track(response)

    async def get_album(self, album_id: str) -> Album:
        response: dict = await self._get(f"https://api.spotify.com/v1/albums/{album_id}")
        return Album(response)

    async def get_artist(self, artist_id: str) -> Artist:
        response: dict = await self._get(f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=DE")
        return Artist(response)

    async def get_playlist(self, playlist_id: str, limit: int = 400) -> Playlist:
        response: dict = await self._get(f"https://api.spotify.com/v1/playlists/{playlist_id}")
        playlist = Playlist(response)

        for i in range(100, limit, 50):
            _response: dict = await self._get(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={i}&limit=50"
            )
            response['tracks']["items"] = _response["items"]
            playlist += Playlist(response)
            if i + 50 >= _response["total"]:
                break
        return playlist  # type: ignore
