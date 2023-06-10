from datetime import datetime, timedelta
from re import match

from aiohttp import ClientSession, ClientResponse

from lib.spotify.album import Album
from lib.spotify.artist import Artist
from lib.spotify.exceptions import SpotifyRateLimit, SpotifyNotFound, SpotifyNotAvailable
from lib.spotify.playlist import Playlist
from lib.spotify.track import Track


class SpotifyAPI:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = None

        self._retry_after = None

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

    def _validate_response_status(self, response: ClientResponse) -> None:
        match response.status:
            case 429:  # Rate limit
                self._retry_after = datetime.now() + timedelta(seconds=int(response.headers["Retry-After"]))
                raise SpotifyRateLimit(retry_after=int(response.headers["Retry-After"]))
            case 200:  # OK
                pass
            case 204:  # No content
                raise SpotifyNotFound()
            case _:
                raise SpotifyNotAvailable(response.reason)

    async def _get(self, url: str) -> dict:
        if not self._token:
            await self._get_token()

        if self._retry_after and datetime.now() < self._retry_after:
            raise SpotifyRateLimit(retry_after=(self._retry_after - datetime.now()).seconds)
        self._retry_after = None

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
